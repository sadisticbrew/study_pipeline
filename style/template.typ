// Pandoc template for study-pipeline chapters. Used by tools/render.py together
// with style/filter.lua; compile with `--input theme=light|dark`.
// (Pandoc template syntax: a literal dollar sign is written as two.)

// ---------------------------------------------------------------- colors
#let theme = sys.inputs.at("theme", default: "light")
#let palettes = (
  light: (
    bg: rgb("#fbf8f1"),
    fg: rgb("#1d1b18"),
    muted: rgb("#6e665a"),
    rule: rgb("#ddd4c3"),
    link: rgb("#076678"),
    accent: rgb("#076678"),
    crux: rgb("#af3a03"),
    crux-tint: rgb("#f6ecdc"),
    aside: rgb("#076678"),
    misconception: rgb("#8f3f71"),
    tryit: rgb("#427b58"),
    warning: rgb("#b0281a"),
    sketch: rgb("#a8650a"),
    code-bg: rgb("#f2ece0"),
    output-bg: rgb("#e9e3d6"),
    output-fg: rgb("#4a443b"),
    zebra: rgb("#f4efe5"),
    // syntax highlighting
    syn-comment: rgb("#8a8172"),
    syn-keyword: rgb("#9d0006"),
    syn-string: rgb("#5f6b0e"),
    syn-number: rgb("#8f3f71"),
    syn-function: rgb("#076678"),
    syn-type: rgb("#a35a00"),
    syn-builtin: rgb("#427b58"),
  ),
  dark: (
    bg: rgb("#282828"),
    fg: rgb("#ebdbb2"),
    muted: rgb("#a89984"),
    rule: rgb("#504945"),
    link: rgb("#83a598"),
    accent: rgb("#83a598"),
    crux: rgb("#fe8019"),
    crux-tint: rgb("#32302f"),
    aside: rgb("#83a598"),
    misconception: rgb("#d3869b"),
    tryit: rgb("#8ec07c"),
    warning: rgb("#fb4934"),
    sketch: rgb("#fabd2f"),
    code-bg: rgb("#32302f"),
    output-bg: rgb("#1d2021"),
    output-fg: rgb("#d5c4a1"),
    zebra: rgb("#2e2c2b"),
    syn-comment: rgb("#928374"),
    syn-keyword: rgb("#fb4934"),
    syn-string: rgb("#b8bb26"),
    syn-number: rgb("#d3869b"),
    syn-function: rgb("#83a598"),
    syn-type: rgb("#fabd2f"),
    syn-builtin: rgb("#8ec07c"),
  ),
)
#assert(theme in palettes, message: "unknown theme '" + theme + "', use light or dark")
#let c = palettes.at(theme)

// ---------------------------------------------------------------- fonts & geometry
#let serif = ("Literata", "Libertinus Serif")
#let sans = ("Inter", "Libertinus Serif")
#let mono = ("JetBrains Mono NL", "DejaVu Sans Mono")
#let note-width = 44mm
#let note-sep = 6mm

#import "@preview/marginalia:0.3.1" as marginalia: note, wideblock

// ---------------------------------------------------------------- syntax theme
#let tm-theme = {
  let rule(scope, color, style: none) = (
    "<dict><key>scope</key><string>" + scope + "</string><key>settings</key><dict>"
      + "<key>foreground</key><string>" + color.to-hex() + "</string>"
      + (if style != none { "<key>fontStyle</key><string>" + style + "</string>" } else { "" })
      + "</dict></dict>"
  )
  bytes(
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?><plist version=\"1.0\"><dict>"
      + "<key>name</key><string>study-" + theme + "</string><key>settings</key><array>"
      + "<dict><key>settings</key><dict><key>foreground</key><string>" + c.fg.to-hex() + "</string></dict></dict>"
      + rule("comment, punctuation.definition.comment", c.syn-comment, style: "italic")
      + rule("string, punctuation.definition.string, constant.character.escape", c.syn-string)
      + rule("constant.numeric, constant.language, constant.character", c.syn-number)
      + rule("keyword, storage, keyword.operator.word", c.syn-keyword)
      + rule("entity.name.function, meta.function-call entity.name, support.function, variable.function", c.syn-function)
      + rule("entity.name.type, entity.name.class, support.type, support.class, storage.type", c.syn-type)
      + rule("support.function.builtin, variable.language, entity.other.attribute-name, meta.decorator", c.syn-builtin)
      + "</array></dict></plist>",
  )
}

// ---------------------------------------------------------------- pandoc writer helpers
#let horizontalRule = line(length: 100%, stroke: 0.5pt + c.rule)
#let divider = (..args) => align(center, line(length: 30%, stroke: 0.5pt + c.rule))

// ---------------------------------------------------------------- small labels
#let label-text(body, color: c.muted, size: 7.5pt) = text(
  font: sans, size: size, weight: 600, tracking: 0.08em, fill: color, upper(body),
)

// ---------------------------------------------------------------- terms
#let term(def: [], key: none, body) = {
  text(weight: 600, body)
  // Word joiner: never break between the term and its (zero-width) note anchor.
  sym.wj
  note(
    counter: none,
    shift: true,
    text-style: (font: sans, size: 7.8pt, fill: c.fg, weight: "regular", style: "normal"),
    par-style: (leading: 0.48em, spacing: 0.6em, justify: false),
  )[#text(weight: 700, if key == none { body } else { key })#h(0.4em)#text(fill: c.muted, def)]
}

// ---------------------------------------------------------------- citations
#let cites(nums, unverified: false) = {
  if nums.len() > 0 {
    let parts = nums.map(n => link(label("src-" + str(n)), str(n)))
    super(typographic: false, size: 0.68em, text(font: sans, [\[] + parts.join([, ]) + [\]]))
  }
  if unverified {
    super(typographic: false, size: 0.62em, text(
      font: sans, weight: 600, tracking: 0.03em, fill: c.warning, "unverified",
    ))
  }
}

#let sources-list(body) = {
  set par(justify: false, leading: 0.55em, spacing: 0.9em)
  set text(size: 9.5pt, hyphenate: false)
  body
}

// The filter attaches <src-N> to each entry; citations link there.
#let source-entry(n, title: "", version: "", url: "") = block(
  above: 0.9em,
  below: 0.9em,
  grid(
    columns: (2.2em, 1fr),
    text(font: sans, size: 8.5pt, fill: c.muted)[\[#n\]],
    [
      #title#if version != "" [, #text(fill: c.muted, version)]#if url != "" [\ #link(url, text(font: mono, size: 8pt, url))]
    ],
  ),
)

// ---------------------------------------------------------------- callouts
#let callout(kind, title: none, body) = {
  let (name, color) = (
    crux: ("The crux", c.crux),
    aside: ("Aside", c.aside),
    misconception: ("Misconception", c.misconception),
    tryit: ("Try it", c.tryit),
  ).at(kind)
  block(
    width: 100%,
    breakable: true,
    above: 1.6em,
    below: 1.6em,
    inset: (left: 12pt, right: if kind == "crux" { 10pt } else { 0pt }, y: if kind == "crux" { 9pt } else { 3pt }),
    stroke: (left: (if kind == "crux" { 2pt } else { 1.2pt }) + color),
    fill: if kind == "crux" { c.crux-tint } else { none },
    {
      block(below: 0.7em, sticky: true, {
        label-text(name, color: color)
        if title != none {
          let t = text(font: sans, size: 10.5pt, weight: 600, fill: c.fg, title)
          block(above: 0.55em, if kind == "misconception" { ["#t"] } else { t })
        }
      })
      if kind == "crux" {
        set text(size: 12pt, style: "italic")
        set par(leading: 0.7em)
        body
      } else { body }
    },
  )
}

// ---------------------------------------------------------------- self-test and answers
#let selftest(body) = block(width: 100%, above: 1.2em, below: 1.6em, {
  set enum(numbering: n => text(font: sans, weight: 600, fill: c.accent, str(n) + "."), spacing: 1.1em)
  body
  v(0.3em)
  text(font: sans, size: 8.5pt, fill: c.muted)[Answers are at #link(<chapter-answers>)[the end of the chapter].]
})

#let answers(body) = {
  set enum(numbering: n => text(font: sans, weight: 600, fill: c.accent, str(n) + "."), spacing: 1.1em)
  body
}

// ---------------------------------------------------------------- code
#let code-frame(kind: "code", lang: none, body) = {
  let (tag, tag-color, bg, stroke) = if kind == "output" {
    ("output", c.muted, c.output-bg, none)
  } else if kind == "sketch" {
    ("sketch, not run", c.sketch, c.code-bg, (left: (paint: c.sketch, thickness: 1pt, dash: "dashed")))
  } else {
    (lang, c.muted, c.code-bg, none)
  }
  let inset = (x: 9pt, top: 8pt, bottom: 8pt)
  let frame(width) = block(
    width: width,
    fill: bg,
    stroke: stroke,
    inset: inset,
    radius: 2pt,
    breakable: true,
    {
      if tag != none {
        place(top + right, dx: 4pt, dy: -5pt, label-text(tag, color: tag-color, size: 6.5pt))
      }
      if kind == "output" {
        set text(fill: c.output-fg)
        body
      } else { body }
    },
  )
  block(above: 1.1em, below: 1.2em, layout(size => {
    let natural = measure(body).width + inset.x * 2 + 18pt
    if natural <= size.width {
      frame(100%)
    } else {
      wideblock(side: "right", frame(calc.min(natural, size.width + note-width + note-sep).to-absolute()))
    }
  }))
}

// ---------------------------------------------------------------- dot diagrams
#let dot-figure(path, caption: none) = {
  let svg = read(path).replace("#a1b2c3", c.fg.to-hex()).replace("#a1b2c4", c.muted.to-hex())
  figure(
    layout(size => {
      let img = image(bytes(svg), format: "svg")
      if measure(img).width > size.width { image(bytes(svg), format: "svg", width: 100%) } else { img }
    }),
    caption: caption,
    kind: image,
  )
}

// ---------------------------------------------------------------- document setup
#set document(title: [$title$])
#show: marginalia.setup.with(
  inner: (far: 18mm, width: 0mm, sep: 0mm),
  outer: (far: 5mm, width: note-width, sep: note-sep),
  top: 22mm,
  bottom: 20mm,
  clearance: 7pt,
)
#set page(
  width: 195mm,
  height: 260mm,
  fill: c.bg,
  header: context {
    if here().page() > 1 {
      set text(font: sans, size: 7.5pt, fill: c.muted)
      block(width: 100% + note-sep + note-width, {
        [$topic$]
        h(1fr)
        [$if(chapter)$Chapter $chapter$ · $endif$$title$]
      })
    }
  },
  footer: context {
    set text(font: sans, size: 7.5pt, fill: c.muted)
    block(width: 100% + note-sep + note-width, {
      h(1fr)
      counter(page).display("1")
    })
  },
)

#set text(font: serif, size: 11pt, fill: c.fg, lang: "en", hyphenate: true, number-type: "lining")
#set par(justify: false, leading: 0.78em, spacing: 1.15em, linebreaks: "optimized")
#set strong(delta: 300)
#show link: set text(fill: c.link)
#show raw: set text(font: mono)
#show raw.where(block: false): it => box(
  fill: c.code-bg, inset: (x: 1.5pt), outset: (x: 0.5pt, y: 2.5pt), radius: 2pt, text(size: 0.88em, it),
)
#show raw.where(block: true): set text(size: 9pt)
#show raw.where(block: true): set par(leading: 0.62em, justify: false)
#set raw(theme: tm-theme)
#show math.equation: set text(fill: c.fg)

#set heading(numbering: none)
#show heading: set text(font: sans, fill: c.fg, hyphenate: false)
#show heading: set par(justify: false, leading: 0.45em)
#show heading.where(level: 2): it => block(above: 2.1em, below: 0.9em, sticky: true,
  text(size: 15pt, weight: 600, it.body))
#show heading.where(level: 3): it => block(above: 1.6em, below: 0.7em, sticky: true,
  text(size: 12pt, weight: 600, it.body))
#show heading.where(level: 4): it => block(above: 1.3em, below: 0.6em, sticky: true,
  text(size: 11pt, weight: 600, it.body))

#set list(indent: 0.4em, body-indent: 0.6em, marker: text(fill: c.muted, [•]))
#set enum(indent: 0.2em, body-indent: 0.6em)
#set terms(hanging-indent: 1.5em)

#set table(
  stroke: none,
  inset: (x: 8pt, y: 5pt),
  fill: (x, y) => if y > 0 and calc.even(y) { c.zebra } else { none },
)
#set table.hline(stroke: 0.6pt + c.rule)
#show table: set text(size: 9.5pt)
#show table: set par(justify: false)
#show table: set align(left)
#show table.cell.where(y: 0): set text(font: sans, weight: 600, size: 8.5pt)
#show figure.where(kind: table): set block(above: 1.4em, below: 1.4em)
#show figure: set block(above: 1.4em, below: 1.4em)
#show figure.caption: set text(font: sans, size: 8.5pt, fill: c.muted)
#show figure.where(kind: table): set figure.caption(position: top)

// ---------------------------------------------------------------- title block
#block(above: 0pt, below: 2.4em, {
  $if(topic)$
  label-text([$topic$], color: c.muted, size: 8pt)
  v(0.9em, weak: true)
  $endif$
  $if(chapter)$
  text(font: sans, size: 12pt, weight: 600, fill: c.accent)[Chapter $chapter$]
  v(0.5em, weak: true)
  $endif$
  show heading.where(level: 1): it => block(text(font: serif, size: 25pt, weight: 600, it.body))
  set par(justify: false, leading: 0.5em)
  heading(level: 1)[$title$]
  v(0.8em)
  line(length: 100%, stroke: 0.5pt + c.rule)
})

$body$
