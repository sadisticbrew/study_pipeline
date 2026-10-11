# Why this exists

This exists because I most of the material I can find on technical topics I want to learn(compiler engineering, ebpf-verifier's internal working, etc) online has the following problem I don't like:

1. It is written too technically what I mean by this is, it starts off right in the weeds.
2. The use of analogies is not much, Like how a teacher explains it is not like that. I want analogies but not much.
3. I straight up get bored and sleepy while reading it.

Example: I was reading kernel docs on ebpf-verifier and it is too 'to the point and no bs'. I also tried reading research papers and docs for raft algo but that is also too in the weeds

This is fine and even preferred when I am in middle of a project and want a reference to solve a bug, plan a feature or lookup something I don't remember and I know the topic/subject of the project somewhat well. But when I want to learn a new topic like compiler-engineering I know a very little about it. I can go spend some time finding resources, then try to read that resource like the dragon book and maybe never finish it because I ran into the problems listed above.

This also adds mental overhead of finding the resources, forcing myself to study even through the material doesn't excite me and then eventually giving up and going into guilt.

I have attempted building such a pipeline before but quit after few chapters generated mainly because the time it was taking to generate every chapter and finding resources was a lot (every chapter took around 2-2.5 hrs depending on the topic).

# What I want from this pipeline

### first

I will tell it a to start a new topic i will do /topic `<subject-name>` and it use llms to search the resources, they might also know many from training data and searching online too from the harness I am running it in (I mostly use oh-my-pi with my opencode-go subscription) and make me a roadmap and outline of what I will be studying/need to study to develop a deep understanding of the subject. (maybe use subagent)

and then ask me what I already know from those topics so I can tick them off.

The above process should not take a long-long amount of time, earlier pipeline took 1-1.5 hrs just to do this.

### second

When I do /chapter `[n]` it should produce that chapter document (markdown and pdf) based on the outline and sources found earlier with an agent swarm.

The biggest problem is that the swarm produces confident, fluent, wrong content for long content writing like this.

It can also include hands on examples, 'why does this exist', common misconceptions or misunderstandings, self test questions, etc.

there will also be a lerner-profile.md file which will contain details about me and is bound to change as I learn things and grow.

All the necessary state should also be preserved between chapters and sessions.

I cannot use very strong models like kimi k3 or glm-5.3 for this thing because the usage I get is very low per month and one session of generation will use almost all my weekly limit from my prior experiences. [usage limits here](https://opencode.ai/docs/go/#usage-limits)

My earlier trial harness used to do researcher, verifier, fact checker, beginner review passes loop 3 times with different models for each agent but that turned out to be very very heavy for an individual's learning and added a lot of time and mental overhead of waiting.

So the problem in this step is how to reduce time taken to generate one chapter drastically while maintaining decent correctness the correctness and generating great quality material using LLMs?

### third (important)

The last concern and the most important one is writing style, tone and general teaching style in the text generated.

One of the best books I ~~read~~ tried reading was OSTEP, it felt like I was sitting in a private lecture of a great professor and he was having a conversation with me. The flow of analogies, explaining in simple terms, going deep whenever necessary and connection he made between topics was chef's kiss. It did have it's flaw though some words it used suddenly were completely new to me and many of those words' meanings led to different rabbit holes.

I like text which explains it simply but doesn't dumb it down to a toddlers intelligence (remember - pipeline is tailored for me) and then takes me to deep, intuitive understanding which makes me an expert on the subject eventually as I finish the roadmap/curriculum generated in first step.

The document should also not look like slop generated from some llm which generally use a lot of semi colons, short punchy sentences like it is saying a pickup line to someone, too much stuff inside parenthesis mid sentence to signify the 'btw' part if it think and so on the general characteristics of slop.

### fourth

I know this plan isn't as perfect as it looks from my perspective, it is bound to change in the future as I learn new things and my preferences evolve but for now I think this is my best hope at competing in this AI driven world by using AI to learn instead of generating slop.

---

The above is what I want from this pipeline, I want your opinion on this, what features are necessary and which are not necessary but okay to have and other thoughts you might have. What should be the consistent style of the pdfs with fonts. We are planning what this should be before building it for real.

I will use this pipeline/framework (what is it) with oh-my-pi ([docs here](https://omp.sh/docs))
