--[[
Pandoc Lua filter that turns a study-pipeline chapter (style/FORMAT.md) into
Typst markup for style/template.typ. Run by tools/render.py, not by hand.

Metadata `render-config` must name a JSON file written by render.py:
  { "chapter": path, "base_dir": dir, "build_dir": dir,
    "facts_path": path, "facts": {F-id: S-id},
    "sources_path": path, "sources": {S-id: {title, url, version}} }

Problems found (missing include, bad lines range, unknown fact or source id,
dot failure) are collected, written one per line to
<build_dir>/filter-errors.txt, and the filter then fails.
]]

local cfg
local errors = {}

local function fail(msg)
  table.insert(errors, msg)
end

local function read_file(path)
  local f = io.open(path, "rb")
  if not f then return nil end
  local s = f:read("a")
  f:close()
  return s
end

local function write_file(path, s)
  local f = assert(io.open(path, "wb"))
  f:write(s)
  f:close()
end

local function is_abs(path)
  return path:sub(1, 1) == "/"
end

local function join(dir, path)
  if is_abs(path) then return path end
  return dir .. "/" .. path
end

-- Typst string literal.
local function typ_str(s)
  s = s:gsub("\\", "\\\\"):gsub('"', '\\"'):gsub("\n", "\\n"):gsub("\r", "\\r"):gsub("\t", "\\t")
  return '"' .. s .. '"'
end

-- Inlines -> Typst markup (escaped by pandoc's own writer).
local function inlines_typst(inls)
  local out = pandoc.write(pandoc.Pandoc({ pandoc.Plain(inls) }), "typst")
  return (out:gsub("%s+$", ""))
end

-- Plain string (attribute value) -> Typst markup, read as Markdown inlines.
local function string_typst(s)
  local doc = pandoc.read(s, "markdown")
  local inls = pandoc.Inlines({})
  for _, b in ipairs(doc.blocks) do
    if b.content then
      if #inls > 0 then inls:insert(pandoc.Space()) end
      inls:extend(b.content)
    end
  end
  return inlines_typst(inls)
end

local function raw_b(s) return pandoc.RawBlock("typst", s) end
local function raw_i(s) return pandoc.RawInline("typst", s) end

---------------------------------------------------------------------------
-- Citations

local source_num = {}   -- S-id -> number
local source_order = {} -- number -> S-id

local function number_cites(doc)
  doc:walk({
    traverse = "topdown",
    Cite = function(c)
      for _, cit in ipairs(c.citations) do
        local id = cit.id
        if id ~= "unverified" then
          local sid = cfg.facts[id]
          if sid == nil then
            local where = cfg.facts_exists and cfg.facts_path or (cfg.facts_path .. " (file does not exist)")
            fail(string.format("citation [@%s] refers to unknown fact id %s; known fact ids in %s: %s",
              id, id, where, cfg.fact_list ~= "" and cfg.fact_list or "none"))
          elseif cfg.sources[sid] ~= nil and source_num[sid] == nil then
            table.insert(source_order, sid)
            source_num[sid] = #source_order
          end
        end
      end
    end,
  })
end

local function cite_typst(c)
  local nums, seen, unverified = {}, {}, false
  for _, cit in ipairs(c.citations) do
    if cit.id == "unverified" then
      unverified = true
    else
      local sid = cfg.facts[cit.id]
      local n = sid and source_num[sid]
      if n and not seen[n] then
        seen[n] = true
        table.insert(nums, n)
      end
    end
  end
  table.sort(nums)
  local arr = {}
  for _, n in ipairs(nums) do table.insert(arr, tostring(n)) end
  return raw_i(string.format("#cites((%s), unverified: %s);",
    table.concat(arr, ", ") .. (#arr == 1 and "," or ""), tostring(unverified)))
end

local function sources_block()
  local lines = {}
  for n, sid in ipairs(source_order) do
    local s = cfg.sources[sid]
    table.insert(lines, string.format("#source-entry(%d, title: %s, version: %s, url: %s) <src-%d>",
      n, typ_str(s.title or ""), typ_str(s.version or ""), typ_str(s.url or ""), n))
  end
  return raw_b("#sources-list[\n" .. table.concat(lines, "\n") .. "\n]")
end

---------------------------------------------------------------------------
-- Code blocks

local function parse_lines(spec, nlines, where)
  local a, b = spec:match("^%s*(%d+)%s*%-%s*(%d+)%s*$")
  if not a then
    a = spec:match("^%s*(%d+)%s*$")
    b = a
  end
  if not a then
    fail(string.format('%s: lines="%s" is not a range; use lines="a-b" (1-based, inclusive)', where, spec))
    return nil
  end
  a, b = tonumber(a), tonumber(b)
  if a < 1 or b < a then
    fail(string.format('%s: lines="%s" is not a valid range; need 1 <= a <= b', where, spec))
    return nil
  end
  if b > nlines then
    fail(string.format('%s: lines="%s" is out of range; the file has only %d lines', where, spec, nlines))
    return nil
  end
  return a, b
end

local function split_lines(text)
  local t = {}
  for line in (text .. "\n"):gmatch("(.-)\r?\n") do table.insert(t, line) end
  if #t > 0 and t[#t] == "" and text:sub(-1) == "\n" then table.remove(t) end
  return t
end

local function include_text(path, spec)
  local where = string.format('include="%s"%s', path, spec and string.format(' lines="%s"', spec) or "")
  local full = join(cfg.base_dir, path)
  local text = read_file(full)
  if text == nil then
    fail(string.format("%s: file not found: %s (include paths are relative to %s)", where, full, cfg.base_dir))
    return nil
  end
  local lines = split_lines(text)
  if spec then
    local a, b = parse_lines(spec, #lines, where)
    if not a then return nil end
    local sel = {}
    for i = a, b do table.insert(sel, lines[i]) end
    lines = sel
  end
  return table.concat(lines, "\n")
end

local dot_count = 0

local function sh_quote(s)
  return "'" .. s:gsub("'", "'\\''") .. "'"
end

local function dot_figure(cb)
  dot_count = dot_count + 1
  local base = string.format("%s/dot-%d", cfg.build_dir, dot_count)
  write_file(base .. ".gv", cb.text)
  -- Placeholder colors are swapped for theme colors by template.typ.
  local args = {
    "-Tsvg",
    "-Gbgcolor=transparent", "-Gfontname=Inter", "-Gfontsize=10", "-Gfontcolor=#a1b2c3",
    "-Ncolor=#a1b2c3", "-Nfontcolor=#a1b2c3", "-Nfontname=Inter", "-Nfontsize=10",
    "-Ecolor=#a1b2c4", "-Efontcolor=#a1b2c3", "-Efontname=Inter", "-Efontsize=9",
    "-o", base .. ".svg", base .. ".gv",
  }
  local cmd = { "dot" }
  for _, a in ipairs(args) do table.insert(cmd, sh_quote(a)) end
  local ok = os.execute(table.concat(cmd, " ") .. " 2> " .. sh_quote(base .. ".err"))
  if not ok then
    local first = cb.text:match("^%s*([^\n]*)") or ""
    local msg = (read_file(base .. ".err") or "dot not found or failed"):gsub("%s+$", "")
    if msg == "" then msg = "dot exited with an error" end
    fail(string.format("dot diagram #%d (starting %q) failed to render: %s", dot_count, first:sub(1, 40), msg))
    return {}
  end
  local cap = cb.attributes.caption
  local cap_t = cap and ("[" .. string_typst(cap) .. "]") or "none"
  return raw_b(string.format("#dot-figure(%s, caption: %s)", typ_str(string.format("dot-%d.svg", dot_count)), cap_t))
end

local function code_block(cb)
  if cb.classes:includes("dot") then return dot_figure(cb) end
  local kind = "code"
  if cb.classes:includes("output") then
    kind = "output"
  elseif cb.classes:includes("sketch") then
    kind = "sketch"
  end
  local lang
  for _, c in ipairs(cb.classes) do
    if c ~= "output" and c ~= "sketch" then
      lang = c
      break
    end
  end
  local text = cb.text
  local inc = cb.attributes.include
  if inc then
    text = include_text(inc, cb.attributes.lines)
    if text == nil then return {} end
  elseif cb.attributes.lines then
    fail(string.format('code block has lines="%s" but no include attribute', cb.attributes.lines))
  end
  local classes = {}
  if lang and kind ~= "output" then classes = { lang } end
  return {
    raw_b(string.format("#code-frame(kind: %s, lang: %s)[", typ_str(kind), lang and typ_str(lang) or "none")),
    pandoc.CodeBlock(text, pandoc.Attr("", classes)),
    raw_b("]"),
  }
end

---------------------------------------------------------------------------
-- Divs and spans

local callout_kinds = { crux = true, aside = true, misconception = true, tryit = true }

local function div(d)
  for _, cls in ipairs(d.classes) do
    if callout_kinds[cls] then
      local title = d.attributes.title
      local title_t = title and ("[" .. string_typst(title) .. "]") or "none"
      local out = { raw_b(string.format("#callout(%s, title: %s)[", typ_str(cls), title_t)) }
      for _, b in ipairs(d.content) do table.insert(out, b) end
      table.insert(out, raw_b("]"))
      return out
    elseif cls == "selftest" then
      local out = { raw_b("#selftest[") }
      for _, b in ipairs(d.content) do table.insert(out, b) end
      table.insert(out, raw_b("]"))
      return out
    end
  end
  return nil
end

local function span(s)
  if not s.classes:includes("term") then return nil end
  local def = s.attributes.def or ""
  local key = s.attributes.key
  local key_t = "none"
  if key and key ~= pandoc.utils.stringify(s.content) then
    key_t = "[" .. string_typst(key) .. "]"
  end
  local out = pandoc.Inlines({ raw_i(string.format("#term(def: [%s], key: %s)[", string_typst(def), key_t)) })
  out:extend(s.content)
  out:insert(raw_i("];"))
  return out
end

-- Drop the space before a citation so the superscript hugs the word.
local function inlines(inls)
  local out = pandoc.Inlines({})
  for _, el in ipairs(inls) do
    if el.t == "Cite" then
      if #out > 0 and (out[#out].t == "Space" or out[#out].t == "SoftBreak") then out:remove(#out) end
      out:insert(cite_typst(el))
    else
      out:insert(el)
    end
  end
  return out
end

---------------------------------------------------------------------------

local function load_config(meta)
  local path = meta["render-config"] and pandoc.utils.stringify(meta["render-config"])
  if not path then error("render-config metadata not set; run this filter through tools/render.py") end
  cfg = pandoc.json.decode(assert(read_file(path), "cannot read " .. path), false)
  cfg.facts = cfg.facts or {}
  cfg.sources = cfg.sources or {}
  local ids = {}
  for id in pairs(cfg.facts) do table.insert(ids, id) end
  table.sort(ids, function(a, b)
    local na, nb = tonumber(a:match("%d+")), tonumber(b:match("%d+"))
    if na and nb and na ~= nb then return na < nb end
    return a < b
  end)
  cfg.fact_list = table.concat(ids, ", ")
end

function Pandoc(doc)
  load_config(doc.meta)
  doc.meta["render-config"] = nil

  -- Raw HTML (comments) never reaches the PDF.
  doc = doc:walk({
    RawBlock = function(r) if r.format ~= "typst" then return {} end end,
    RawInline = function(r) if r.format ~= "typst" then return {} end end,
  })

  -- Pull answers out; they go to the end.
  local answers = {}
  doc = doc:walk({
    Div = function(d)
      if d.classes:includes("answers") then
        for _, b in ipairs(d.content) do table.insert(answers, b) end
        return {}
      end
    end,
  })
  local blocks = doc.blocks
  if #answers > 0 then
    blocks:insert(pandoc.Header(2, "Answers", pandoc.Attr("chapter-answers")))
    blocks:insert(raw_b("#answers["))
    blocks:extend(answers)
    blocks:insert(raw_b("]"))
  end
  doc.blocks = blocks

  number_cites(doc)

  doc = doc:walk({ Inlines = inlines, Span = span })
  doc = doc:walk({ CodeBlock = code_block, Div = div })

  if #source_order > 0 then
    doc.blocks:insert(pandoc.Header(2, "Sources", pandoc.Attr("chapter-sources")))
    doc.blocks:insert(sources_block())
  end

  -- Every fact must point at a known source, cited or not.
  local fids = {}
  for id in pairs(cfg.facts) do table.insert(fids, id) end
  table.sort(fids)
  for _, id in ipairs(fids) do
    local sid = cfg.facts[id]
    if cfg.sources[sid] == nil then
      local where = cfg.sources_exists and cfg.sources_path or (cfg.sources_path .. " (file does not exist)")
      fail(string.format("fact %s in %s refers to unknown source id %s; it is not in %s",
        id, cfg.facts_path, tostring(sid), where))
    end
  end

  local err_path = cfg.build_dir .. "/filter-errors.txt"
  if #errors > 0 then
    write_file(err_path, table.concat(errors, "\n") .. "\n")
    error(string.format("%d problem(s), see %s", #errors, err_path))
  end
  os.remove(err_path)
  return doc
end
