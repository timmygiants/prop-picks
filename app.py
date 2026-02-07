import streamlit as st
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

# Page config
st.set_page_config(
    page_title="Super Bowl Prop Picks",
    page_icon="🏈",
    layout="wide"
)

# Data file
DATA_FILE = "picks.json"
RESULTS_FILE = "results.json"

# Initialize session state
if "submitted" not in st.session_state:
    st.session_state.submitted = False

def load_picks() -> List[Dict]:
    """Load picks from JSON file"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

def save_picks(picks: List[Dict]):
    """Save picks to JSON file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(picks, f, indent=2)

def load_results() -> Dict:
    """Load actual results from JSON file"""
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_results(results: Dict):
    """Save actual results to JSON file"""
    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)

def calculate_score(picks: Dict, results: Dict) -> int:
    """Calculate score based on picks vs results"""
    if not results:
        return 0
    
    score = 0
    points = {
        'winner': 10,
        'total_points': 10,
        'mvp': 10,
        'first_touchdown': 5,
        'coin_toss': 3,
        'national_anthem_duration': 5,
        'first_commercial_category': 3,
        'halftime_performer_song': 3,
        'gatorade_color': 5,
        'first_score_type': 5
    }
    
    # Check each pick
    for key, points_value in points.items():
        if key in picks and key in results:
            if picks[key] == results[key]:
                score += points_value
    
    return score

def main():
    st.title("🏈 Super Bowl Prop Picks")
    st.markdown("---")
    
    # Sidebar for admin (results entry)
    with st.sidebar:
        st.header("⚙️ Admin")
        if st.checkbox("Enter Results (Admin Only)"):
            st.subheader("Enter Actual Results")
            results = load_results()
            
            winner = st.selectbox("Winner", ["", "Kansas City Chiefs", "San Francisco 49ers"], 
                                index=0 if not results.get('winner') else (1 if results.get('winner') == "Kansas City Chiefs" else 2))
            total_points = st.number_input("Total Points", min_value=0, value=results.get('total_points', 0))
            mvp = st.text_input("MVP", value=results.get('mvp', ''))
            first_touchdown = st.text_input("First Touchdown Scorer", value=results.get('first_touchdown', ''))
            coin_toss = st.selectbox("Coin Toss", ["", "Heads", "Tails"], 
                                    index=0 if not results.get('coin_toss') else (1 if results.get('coin_toss') == "Heads" else 2))
            national_anthem_duration = st.number_input("National Anthem Duration (seconds)", 
                                                      min_value=0.0, value=results.get('national_anthem_duration', 0.0), step=0.1)
            first_commercial_category = st.text_input("First Commercial Category", value=results.get('first_commercial_category', ''))
            halftime_performer_song = st.text_input("Halftime Performer First Song", value=results.get('halftime_performer_song', ''))
            gatorade_color = st.selectbox("Gatorade Shower Color", 
                                        ["", "Orange", "Yellow", "Green", "Blue", "Purple", "Red", "Clear/Water"],
                                        index=0 if not results.get('gatorade_color') else 
                                        ["", "Orange", "Yellow", "Green", "Blue", "Purple", "Red", "Clear/Water"].index(results.get('gatorade_color', '')))
            first_score_type = st.selectbox("First Score Type", 
                                           ["", "Touchdown", "Field Goal", "Safety"],
                                           index=0 if not results.get('first_score_type') else 
                                           ["", "Touchdown", "Field Goal", "Safety"].index(results.get('first_score_type', '')))
            
            if st.button("Save Results"):
                new_results = {
                    'winner': winner if winner else None,
                    'total_points': int(total_points) if total_points else None,
                    'mvp': mvp if mvp else None,
                    'first_touchdown': first_touchdown if first_touchdown else None,
                    'coin_toss': coin_toss if coin_toss else None,
                    'national_anthem_duration': float(national_anthem_duration) if national_anthem_duration else None,
                    'first_commercial_category': first_commercial_category if first_commercial_category else None,
                    'halftime_performer_song': halftime_performer_song if halftime_performer_song else None,
                    'gatorade_color': gatorade_color if gatorade_color else None,
                    'first_score_type': first_score_type if first_score_type else None,
                    'updated_at': datetime.now().isoformat()
                }
                save_results(new_results)
                st.success("Results saved!")
                st.rerun()
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📝 Submit Picks", "📊 Leaderboard", "📋 All Picks"])
    
    with tab1:
        st.header("Submit Your Prop Picks")
        
        with st.form("picks_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Your Name *", placeholder="Enter your name")
                email = st.text_input("Email *", placeholder="your.email@example.com")
            
            st.markdown("### Game Props")
            
            col1, col2 = st.columns(2)
            with col1:
                winner = st.selectbox("Winner *", ["", "Kansas City Chiefs", "San Francisco 49ers"])
                total_points = st.number_input("Total Points *", min_value=0, value=50, step=1)
                mvp = st.text_input("MVP *", placeholder="Player name")
                first_touchdown = st.text_input("First Touchdown Scorer", placeholder="Player name")
            
            with col2:
                coin_toss = st.selectbox("Coin Toss", ["", "Heads", "Tails"])
                first_score_type = st.selectbox("First Score Type", ["", "Touchdown", "Field Goal", "Safety"])
                gatorade_color = st.selectbox("Gatorade Shower Color", 
                                            ["", "Orange", "Yellow", "Green", "Blue", "Purple", "Red", "Clear/Water"])
            
            st.markdown("### Entertainment Props")
            
            col1, col2 = st.columns(2)
            with col1:
                national_anthem_duration = st.number_input("National Anthem Duration (seconds)", 
                                                          min_value=0.0, value=120.0, step=0.1)
                first_commercial_category = st.text_input("First Commercial Category", 
                                                         placeholder="e.g., Beer, Car, Insurance")
            
            with col2:
                halftime_performer_song = st.text_input("Halftime Performer First Song", 
                                                       placeholder="Song name")
            
            submitted = st.form_submit_button("Submit Picks", type="primary")
            
            if submitted:
                if not name or not email:
                    st.error("Please fill in your name and email!")
                elif not winner or not mvp or total_points == 0:
                    st.error("Please fill in all required fields (marked with *)")
                else:
                    picks = load_picks()
                    
                    # Check if email already exists
                    if any(p['email'].lower() == email.lower() for p in picks):
                        st.error("This email has already submitted picks!")
                    else:
                        new_pick = {
                            'name': name,
                            'email': email.lower(),
                            'winner': winner,
                            'total_points': int(total_points),
                            'mvp': mvp,
                            'first_touchdown': first_touchdown if first_touchdown else None,
                            'coin_toss': coin_toss if coin_toss else None,
                            'national_anthem_duration': float(national_anthem_duration) if national_anthem_duration else 0.0,
                            'first_commercial_category': first_commercial_category if first_commercial_category else None,
                            'halftime_performer_song': halftime_performer_song if halftime_performer_song else None,
                            'gatorade_color': gatorade_color if gatorade_color else None,
                            'first_score_type': first_score_type if first_score_type else None,
                            'submitted_at': datetime.now().isoformat()
                        }
                        
                        picks.append(new_pick)
                        save_picks(picks)
                        st.session_state.submitted = True
                        st.success(f"✅ Picks submitted successfully, {name}!")
                        st.balloons()
    
    with tab2:
        st.header("🏆 Leaderboard")
        
        picks = load_picks()
        results = load_results()
        
        if not picks:
            st.info("No picks submitted yet. Be the first to submit!")
        else:
            # Calculate scores
            leaderboard_data = []
            for pick in picks:
                score = calculate_score(pick, results)
                leaderboard_data.append({
                    'Name': pick['name'],
                    'Score': score,
                    'Winner': pick['winner'],
                    'Total Points': pick['total_points'],
                    'MVP': pick['mvp']
                })
            
            # Sort by score (descending)
            leaderboard_data.sort(key=lambda x: x['Score'], reverse=True)
            
            # Display leaderboard
            df = pd.DataFrame(leaderboard_data)
            
            if results:
                st.success("✅ Results have been entered! Scores are now live.")
            else:
                st.info("⏳ Waiting for results to be entered. Scores will update automatically.")
            
            # Add rank column
            df.insert(0, 'Rank', range(1, len(df) + 1))
            
            # Highlight top 3
            st.dataframe(
                df.style.apply(
                    lambda x: ['background-color: #FFD700' if x.name < 1 else 
                              'background-color: #C0C0C0' if x.name < 2 else
                              'background-color: #CD7F32' if x.name < 3 else '' 
                              for _ in x], axis=1
                ),
                use_container_width=True,
                hide_index=True
            )
            
            # Show top 3 with emojis
            if len(df) > 0:
                st.markdown("### 🏅 Top 3")
                for idx, row in df.head(3).iterrows():
                    medal = "🥇" if row['Rank'] == 1 else "🥈" if row['Rank'] == 2 else "🥉"
                    st.markdown(f"{medal} **{row['Name']}** - {row['Score']} points")
    
    with tab3:
        st.header("All Submitted Picks")
        
        picks = load_picks()
        results = load_results()
        
        if not picks:
            st.info("No picks submitted yet.")
        else:
            for i, pick in enumerate(picks, 1):
                with st.expander(f"{pick['name']} - Submitted {pick['submitted_at'][:10]}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Game Props:**")
                        st.write(f"Winner: {pick['winner']}")
                        st.write(f"Total Points: {pick['total_points']}")
                        st.write(f"MVP: {pick['mvp']}")
                        if pick.get('first_touchdown'):
                            st.write(f"First Touchdown: {pick['first_touchdown']}")
                        if pick.get('first_score_type'):
                            st.write(f"First Score Type: {pick['first_score_type']}")
                    
                    with col2:
                        st.write("**Other Props:**")
                        if pick.get('coin_toss'):
                            st.write(f"Coin Toss: {pick['coin_toss']}")
                        if pick.get('gatorade_color'):
                            st.write(f"Gatorade Color: {pick['gatorade_color']}")
                        if pick.get('national_anthem_duration'):
                            st.write(f"National Anthem: {pick['national_anthem_duration']}s")
                        if pick.get('first_commercial_category'):
                            st.write(f"First Commercial: {pick['first_commercial_category']}")
                        if pick.get('halftime_performer_song'):
                            st.write(f"Halftime Song: {pick['halftime_performer_song']}")
                    
                    if results:
                        score = calculate_score(pick, results)
                        st.metric("Current Score", f"{score} points")

if __name__ == "__main__":
    main()
