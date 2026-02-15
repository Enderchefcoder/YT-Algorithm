use std::collections::HashMap;

// === DATA ===

struct VideoWatch {
    watch_time: f64,       // how long they actually watched (seconds)
    video_length: f64,     // full video length (seconds)
    video_name: String,
    hashtags: Vec<String>,
    liked: bool,
    disliked: bool,
    watched_at: u64,       // just a counter. 1 = first video, 2 = second, and so on
}

impl VideoWatch {
    fn attention_ratio(&self) -> f64 {
        if self.video_length == 0.0 {
            return 0.0; // don't divide by zero, obviously
        }
        self.watch_time / self.video_length
    }
}

// === GUARDRAILS ===

struct Guardrails {
    attention_scores: Vec<f64>,
    session_time_secs: f64,
    current_hour: u8,                  // 0-23 (24 hours)
    parent_break_override: Option<f64>, // parents can force a break length
}

impl Guardrails {
    fn new(hour: u8) -> Guardrails {
        Guardrails {
            attention_scores: Vec::new(),
            session_time_secs: 0.0,
            current_hour: hour,
            parent_break_override: None,
        }
    }

    fn record(&mut self, watch: &VideoWatch) {
        // under 7 seconds? probably a misclick or scroll-past. ignore it
        if watch.watch_time < 7.0 {
            return;
        }
        self.attention_scores.push(watch.attention_ratio());
        self.session_time_secs += watch.watch_time;
    }

    fn avg_attention(&self) -> f64 {
        if self.attention_scores.is_empty() {
            return 1.0; // no data yet, assume they're fine
        }
        let sum: f64 = self.attention_scores.iter().sum();
        sum / self.attention_scores.len() as f64
    }

    fn break_length_minutes(&self) -> f64 {
        // parents get final say
        if let Some(mins) = self.parent_break_override {
            return mins;
        }

        // base is 5 min, scales up the later it gets
        // midnight would technically be 0 but nobody should be up that late anyway(but everyone is)
        let base = 5.0;
        let hour_scale = self.current_hour as f64 / 24.0;
        base + (base * hour_scale)
        // examples:
        //   8 am  -> 6.7 min (67!)
        //   noon -> 7.5 min
        //   9 pm  -> 9.4 min
    }

    fn should_break(&self) -> bool {
        let session_min = self.session_time_secs / 60.0;

        // hard limit. 20 minutes straight, take a break
        if session_min > 20.0 {
            return true;
        }

        // if you're barely watching anything AND you've been at it for 8+ min,
        // you're probably just doomscrolling. stop that now.
        // we aren't youtube, and therefore we care about your health
      if self.avg_attention() < 0.25 && session_min > 8.0 {
            return true;
        }

        false
    }

    // call this at midnight or whatever
    fn reset_daily(&mut self) {
        self.attention_scores.clear();
    }
}

// === FEED ENGINE ===

struct FeedEngine {
    history: Vec<VideoWatch>,
    blacklist: Vec<String>,
}

impl FeedEngine {
    fn new() -> FeedEngine {
        FeedEngine {
            history: Vec::new(),
            blacklist: Vec::new(),
        }
    }

    fn add_watch(&mut self, watch: VideoWatch) {
        // disliked = "i don't want this." block everything about it
        if watch.disliked {
            for tag in &watch.hashtags {
                self.blacklist.push(tag.to_lowercase());
            }
            for word in watch.video_name.to_lowercase().split_whitespace() {
                self.blacklist.push(word.to_string());
            }
        }
        self.history.push(watch);
    }

    // pull every(usable) word from history
    // newer videos get repeated more so they show up stronger
    // liked videos get extra weight
    fn extract_words(&self) -> Vec<String> {
        let mut words: Vec<String> = Vec::new();
        let len = self.history.len();

        if len == 0 {
            return words;
        }

        for (i, watch) in self.history.iter().enumerate() {
            if watch.disliked {
                continue; // skip stuff they hated/disliked
            }

            // recency weighting so we have newer videos appear more
            // newest video in a list of 10 gets 3x weight
            // oldest gets 1x
            let weight = (i + 1) as f64 / len as f64;
            let repeats = (weight * 3.0).ceil() as usize;

            for _ in 0..repeats {
                // title words
                for word in watch.video_name.to_lowercase().split_whitespace() {
                    let w = word.to_string();
                    if !self.blacklist.contains(&w) {
                        words.push(w);
                    }
                }
                // hashtags
                for tag in &watch.hashtags {
                    let t = tag.to_lowercase();
                    if !self.blacklist.contains(&t) {
                        words.push(t);
                    }
                }
                // liked? double the weight. you clearly care about this topic
                if watch.liked {
                    for tag in &watch.hashtags {
                        let t = tag.to_lowercase();
                        if !self.blacklist.contains(&t) {
                            words.push(t);
                        }
                    }
                }
            }
        }

        words
    }

    // markov chain: for each word, what words tend to come after it?
    fn build_markov(&self, words: &[String]) -> HashMap<String, Vec<String>> {
        let mut chain: HashMap<String, Vec<String>> = HashMap::new();

        // groups of 2: [a,b], [b,c], [c,d]...
        for window in words.windows(2) {
            chain
                .entry(window[0].clone())
                .or_insert_with(Vec::new)
                .push(window[1].clone());
        }

        chain
    }

    // walk the chain. start at a word, follow links, collect unique results
    fn walk_markov(
        &self,
        chain: &HashMap<String, Vec<String>>,
        start: &str,
        steps: usize,
    ) -> Vec<String> {
        let mut result = vec![start.to_string()];
        let mut current = start.to_string();

        for i in 0..steps {
            match chain.get(&current) {
                Some(nexts) => {
                    // just rotating through options for now
                    // we should swap this for rand if we want real randomness, but this is a demo
                    let pick = nexts[i % nexts.len()].clone();
                    current = pick.clone();
                    if !result.contains(&pick) {
                        result.push(pick);
                    }
                }
                None => break,
            }
        }

        result
    }

    // tf-idf: figure out which words actually matter
    // "how" and "to" appear in everything -> low score
    // "carbonara" appears in one video a lot -> high score
    fn tfidf_top_words(&self, n: usize) -> Vec<String> {
        // each video = one "document"
        let docs: Vec<Vec<String>> = self.history.iter()
            .filter(|w| !w.disliked)
            .map(|w| {
                let mut doc_words: Vec<String> = w.video_name
                    .to_lowercase()
                    .split_whitespace()
                    .map(|s| s.to_string())
                    .collect();
                for tag in &w.hashtags {
                    doc_words.push(tag.to_lowercase());
                }
                doc_words
            })
            .collect();

        if docs.is_empty() {
            return Vec::new();
        }

        let total_docs = docs.len() as f64;
        let mut scores: HashMap<String, f64> = HashMap::new();

        for doc in &docs {
            let doc_len = doc.len() as f64;

            // count how often each word appears in THIS document
            let mut tf: HashMap<String, f64> = HashMap::new();
            for word in doc {
                *tf.entry(word.clone()).or_insert(0.0) += 1.0;
            }

            for (word, count) in &tf {
                if self.blacklist.contains(word) {
                    continue;
                }

                let tf_score = count / doc_len;

                // how many documentss even have this word?
                let docs_with_word = docs.iter()
                    .filter(|d| d.contains(word))
                    .count() as f64;

                // rare word across docs = high idf
                let idf = (total_docs / docs_with_word).ln();

                *scores.entry(word.clone()).or_insert(0.0) += tf_score * idf;
            }
        }

        // sort highest score first
        let mut scored: Vec<(String, f64)> = scores.into_iter().collect();
        scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());

        scored.into_iter()
            .take(n)
            .map(|(word, _)| word)
            .collect()
    }

    // THE MAIN THING
    // hybrid: half tfidf, half markov
    fn generate_query(&self, word_count: usize) -> Vec<String> {
        // nothing watched yet? just show trending
        if self.history.is_empty() {
            return vec![String::from("trending")];
        }

        let words = self.extract_words();
        if words.is_empty() {
            return vec![String::from("trending")];
        }

        let half = word_count / 2;

        // tfidf picks the words that actually matter
        let tfidf_words = self.tfidf_top_words(half);

        // markov walks from one of those words for some variety
        let chain = self.build_markov(&words);
        let start = if !tfidf_words.is_empty() {
            tfidf_words[0].as_str()
        } else {
            words[0].as_str()
        };
        let markov_words = self.walk_markov(&chain, start, half);

        // merge, no duplicates
        let mut result: Vec<String> = Vec::new();
        for w in tfidf_words {
            if !result.contains(&w) {
                result.push(w);
            }
        }
        for w in markov_words {
            if !result.contains(&w) {
                result.push(w);
            }
        }

        result.truncate(word_count);
        result
    }
}

// === MAIN ===

fn main() {
    let mut engine = FeedEngine::new();
    let mut guardrails = Guardrails::new(21); // 9 PM

    // --- simulate some watches ---

    let w1 = VideoWatch {
        watch_time: 100.0,
        video_length: 120.0,
        video_name: String::from("How to make pasta carbonara"),
        hashtags: vec![
            String::from("cooking"),
            String::from("pasta"),
            String::from("italian"), // note to self: don't pineapple the pizza
        ],
        liked: true,
        disliked: false,
        watched_at: 1,
    };
    guardrails.record(&w1);
    engine.add_watch(w1);

    let w2 = VideoWatch {
        watch_time: 200.0,
        video_length: 300.0,
        video_name: String::from("Italian cooking secrets from grandma"), // she has many
        hashtags: vec![
            String::from("cooking"),
            String::from("italian"), // a second one. i think they found out about the pineapple
            String::from("recipes"),
        ],
        liked: false,
        disliked: false,
        watched_at: 2,
    };
    guardrails.record(&w2);
    engine.add_watch(w2);

    let w3 = VideoWatch {
        watch_time: 180.0,
        video_length: 200.0,
        video_name: String::from("Best pasta shapes ranked by an italian chef"),
        hashtags: vec![
            String::from("pasta"),
            String::from("italian"), // hide the pineapple! and the pizza its on!
            String::from("food"),
        ],
        liked: true,
        disliked: false,
        watched_at: 3,
    };
    guardrails.record(&w3);
    engine.add_watch(w3);

    // this one gets disliked
    let w4 = VideoWatch {
        watch_time: 3.0, // barely watched, under 5s so guardrails ignore it
        video_length: 600.0,
        video_name: String::from("Clickbait garbage you wont believe"), // I don't believe it
        hashtags: vec![
            String::from("shocking"),
            String::from("viral"),
        ],
        liked: false,
        disliked: true,
        watched_at: 4,
    };
    guardrails.record(&w4);
    engine.add_watch(w4);

    // --- results ---

    println!("=== GUARDRAILS ===");
    println!("avg attention:  {:.0}%", guardrails.avg_attention() * 100.0);
    println!("session so far: {:.1} min", guardrails.session_time_secs / 60.0);
    println!("need a break:   {}", guardrails.should_break());
    println!("break would be: {:.1} min", guardrails.break_length_minutes());

    println!();
    println!("=== FEED ===");
    let query = engine.generate_query(8);
    println!("search words: {:?}", query);
    println!("(you'd pass these to a search api and show the results)");

    println!();
    println!("=== DISLIKED ===");
    println!("{:?}", engine.blacklist);
                      }
