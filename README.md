

# YT-Algorithm
A new project cloning the YouTube algorithm, with safety guardrails.

## Architecture
> User: Watches
Collect, for each video, Watch Time(A), Video Time(B), Time Watching(C), Video Name(D), Video Hashtags(E), Liked Video(F), Disliked Video(G), Current Hour(H).

### 1 - GUARDRAILS
> A, B -> Attention Span %
(statistics are collected per day and reset after use)
(watches under 5 seconds are thrown out)
IF % < 25 AND C > 8 minutes, lock(break)
IF C > 20 minutes, lock(break)
Break does NOT cut a video mid-play. Waits until it ends.
Break length scales with H. Later = longer break. Base 3 minutes. Max 10.
Parents can increase break lengths(i.e. 10, 30, 60).

### 2 - FEED
> D, E, F, G -> Input
G removes associated hashtags/words from input.
Recent watches are weighted heavier than old ones.
HYBRID(MARKOV_CHAIN, TF-IDF)(Input) (output 8 words) -> SEARCH OUTPUT WORDS -> RETURN RESULTS TO FEED
IF history is empty, pull trending.

## TODO
- Implement in Rust (☆)
- Right now, it just feeds the search from the hybrid output. Can we make it so it makes 8 batches based on #'s and feeds THOSE to the feed? (◇)
- Decide how fast old watches decay in weight (○)

- ☆ = IMPORTANT
- ◇ = FEATURE
- ○ = NOT REQUIRED
