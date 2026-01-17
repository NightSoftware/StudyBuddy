StudyBuddy - Spaced Repetition Tool 🧠

StudyBuddy is a simple CLI-based tool I built to help with long-term memorization. It uses the SM-2 (SuperMemo-2) algorithm to calculate exactly when you should review your flashcards based on how well you know the material.

Why I built this
I wanted a way to manage study decks without the clutter of complex apps. This project focuses on the core logic: creating decks, adding cards, and getting a "due list" for the day so you never miss a review session.

Key Features
Smart Scheduling: Uses the SM-2 algorithm to adjust review intervals dynamically.

File Safety: Implements atomic writes to make sure your data doesn't get corrupted if the app crashes.

Persistent Storage: Everything is saved in JSON format under the data/ folder.

Logged Activity: All major actions are tracked in studybuddy.log for debugging and history.

How to run it
-Clone the repo.

-Make sure you have Python installed.

-Run the main script:


python main.py
To run the test suite:



python -m unittest discover tests
Project Structure
main.py: The heart of the app.

data/: Where your study progress lives.

tests/: Unit tests to ensure the logic stays solid.
