from __future__ import annotations

from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

DATASET = [
    ("My manager yelled at me in front of the team and called me useless.", "verbal harassment"),
    ("A senior mocked my accent repeatedly during meetings.", "verbal harassment"),
    ("Coworkers insult me every day and shout when I ask questions.", "verbal harassment"),
    ("He threatened me verbally and humiliated me in the office.", "verbal harassment"),
    ("She sent inappropriate messages to me late at night on Slack.", "digital harassment"),
    ("My colleague keeps emailing offensive jokes and harassing me online.", "digital harassment"),
    ("I received unwanted DMs and abusive texts after work hours.", "digital harassment"),
    ("Someone shared private photos and blackmailed me through chat.", "digital harassment"),
    ("A coworker touched me without consent near the pantry.", "physical harassment"),
    ("He grabbed my arm and blocked the door when I tried to leave.", "physical harassment"),
    ("I was pushed during an argument in the workplace.", "physical harassment"),
    ("A teammate slapped me and threatened more violence.", "physical harassment"),
    ("The issue does not fit the main categories but still feels unsafe.", "other"),
    ("I want to report discrimination and retaliation that happened after my complaint.", "other"),
    ("There was repeated hostile behavior that is hard to classify.", "other"),
    ("People have been excluding me and spreading rumors indirectly.", "other"),
    ("My boss screamed at me and called me stupid during standup.", "verbal harassment"),
    ("I got threatening WhatsApp messages from a colleague.", "digital harassment"),
    ("Someone cornered me and tried to touch me inappropriately.", "physical harassment"),
    ("Anonymous emails with humiliating content were sent to me.", "digital harassment"),
    ("A person in the office repeatedly mocked my appearance.", "verbal harassment"),
    ("I was shoved in the hallway after rejecting advances.", "physical harassment"),
]


def main() -> None:
    texts = [text for text, _ in DATASET]
    labels = [label for _, label in DATASET]

    pipeline = Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, stop_words="english")),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    pipeline.fit(texts, labels)

    output_path = Path("backend/model_artifacts/harassment_classifier.joblib")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, output_path)
    print(f"Saved model to {output_path}")


if __name__ == "__main__":
    main()
