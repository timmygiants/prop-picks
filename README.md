# 🏈 Super Bowl Prop Picks

A Streamlit application for collecting and tracking Super Bowl prop bet picks with automatic leaderboard scoring.

## Features

- 📝 **Submit Picks**: Easy form to submit your Super Bowl prop predictions
- 📊 **Live Leaderboard**: Automatically calculates and displays scores based on actual results
- 📋 **View All Picks**: See everyone's submissions
- ⚙️ **Admin Panel**: Enter actual results to calculate scores

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the app:**
   ```bash
   streamlit run app.py
   ```

3. **Access the app:**
   - The app will open in your browser automatically
   - Default URL: http://localhost:8501

## How to Use

### For Participants

1. Go to the "Submit Picks" tab
2. Fill in your name and email
3. Make your predictions for each prop
4. Click "Submit Picks"

### For Admins

1. Check the "Enter Results (Admin Only)" checkbox in the sidebar
2. Enter the actual results after the game
3. Click "Save Results"
4. The leaderboard will automatically update with scores

## Scoring System

- Winner: 10 points
- Total Points: 10 points
- MVP: 10 points
- First Touchdown Scorer: 5 points
- Gatorade Shower Color: 5 points
- First Score Type: 5 points
- National Anthem Duration: 5 points
- Coin Toss: 3 points
- First Commercial Category: 3 points
- Halftime Performer Song: 3 points

## Question Configuration

Since Google Forms exports don't include answer options, questions are configured in `question_config.json`. This file maps each question to its type and options:

- **select**: Dropdown with specific options (e.g., "Heads/Tails", "Even/Odd")
- **over_under**: Over/Under question with a threshold number
- **yes_no**: Yes/No question
- **text**: Free text input
- **number**: Number input

To add or modify questions:
1. Edit `question_config.json`
2. Use the exact question text from your Excel file as the key
3. Specify the `type` and `options` (or `threshold` for over/under)

Questions not in the config file will use automatic detection based on question text patterns.

## Data Storage

- Picks are stored in `picks.json`
- Results are stored in `results.json`
- Question configuration is in `question_config.json`
- All files are created automatically on first use

## Notes

- Each email can only submit picks once
- Scores are calculated automatically when results are entered
- The leaderboard updates in real-time
- Admin password: `Pr0pP!cks` (set in code)

## License

MIT
