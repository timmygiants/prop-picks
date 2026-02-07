import streamlit as st
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
import re
import hashlib

# Page config
st.set_page_config(
    page_title="Super Bowl LX Prop Picks",
    page_icon="🏈",
    layout="wide"
)

# Data files
DATA_FILE = "picks.json"
RESULTS_FILE = "results.json"
QUESTIONS_FILE = "Super Bowl LX Picks.xlsx"

# Initialize session state
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "questions" not in st.session_state:
    st.session_state.questions = None

def load_questions() -> List[Dict]:
    """Load questions from Excel file"""
    if st.session_state.questions is not None:
        return st.session_state.questions
    
    try:
        df = pd.read_excel(QUESTIONS_FILE)
        
        # Exclude metadata columns
        exclude_cols = [
            'Timestamp', 
            'Email Address', 
            'Name',
            'Would you like to opt-in for $20 SUPER BOWL POOL - Half of winnings go to charity of winner\'s choice and other half in their pocker.  Send a $20 Venmo to @john-deely-67',
            'Did you Venmo $20 to @john-deely-67',
            'For auditing purposes, what is your Venmo handle? (Please include @ in the handle or just Venmo me)',
            'If you win, what is your charity of choice? (Please don\'t say "idk" like Aaron Black)'
        ]
        
        questions = []
        for col in df.columns:
            if col not in exclude_cols:
                q_type, options = determine_question_type(col)
                questions.append({
                    'key': col,
                    'text': col,
                    'type': q_type,
                    'options': options,
                    'required': 'TIE BREAKER' not in col.upper()  # Tie breaker is optional
                })
        
        st.session_state.questions = questions
        return questions
    except Exception as e:
        st.error(f"Error loading questions: {str(e)}")
        return []

def determine_question_type(question_text: str) -> Tuple[str, List]:
    """Determine question type and options based on question text"""
    q_lower = question_text.lower()
    
    # Over/Under questions
    if 'over/under' in q_lower:
        # Extract the number
        match = re.search(r'over/under\s+([\d.]+)', q_lower)
        if match:
            threshold = float(match.group(1))
            return 'over_under', [threshold]
        return 'over_under', [0]
    
    # Yes/No questions
    if q_lower.startswith('will ') or 'will ' in q_lower:
        return 'yes_no', []
    
    # Heads or Tails
    if 'heads or tails' in q_lower or 'heads/tails' in q_lower:
        return 'select', ['Heads', 'Tails']
    
    # Even or Odd
    if 'even or odd' in q_lower:
        return 'select', ['Even', 'Odd']
    
    # Up or Down
    if 'up or down' in q_lower:
        return 'select', ['Up', 'Down']
    
    # Multiple choice with "or"
    if ' or ' in question_text and not 'over/under' in q_lower:
        # Try to extract options
        parts = question_text.split(' or ')
        if len(parts) == 2:
            # Clean up the options
            opt1 = parts[0].split(':')[-1].strip() if ':' in parts[0] else parts[0].strip()
            opt2 = parts[1].split('?')[0].strip() if '?' in parts[1] else parts[1].strip()
            # Remove common prefixes
            opt1 = re.sub(r'^(which|who|what|more|first)\s+', '', opt1, flags=re.IGNORECASE).strip()
            opt2 = re.sub(r'^(which|who|what|more|first)\s+', '', opt2, flags=re.IGNORECASE).strip()
            if opt1 and opt2:
                return 'select', [opt1, opt2]
    
    # Gatorade color
    if 'gatorade' in q_lower and 'color' in q_lower:
        return 'select', ['Orange', 'Yellow', 'Green', 'Blue', 'Purple', 'Red', 'Clear/Water', 'None']
    
    # First play type
    if 'first play' in q_lower and ('run' in q_lower or 'pass' in q_lower):
        return 'select', ['Run', 'Pass/Sack']
    
    # Turnover type
    if 'first turnover' in q_lower:
        return 'select', ['Fumble', 'Interception', 'Turnover on Downs', 'None']
    
    # Car commercial type
    if 'car commercial' in q_lower:
        return 'select', ['Gas', 'Electric', 'Hybrid']
    
    # Pharmaceutical commercial
    if 'pharmaceutical' in q_lower:
        return 'select', ['Weight Loss/Diabetes', 'Other']
    
    # Coach selection (for National Anthem)
    if 'coach' in q_lower and 'national anthem' in q_lower:
        return 'select', ['Seattle Seahawks Coach', 'New England Patriots Coach']
    
    # Coin toss winner
    if 'who wins coin toss' in q_lower:
        return 'select', ['Seattle Seahawks', 'New England Patriots']
    
    # Default to text input
    return 'text', []

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

def calculate_score(picks: Dict, results: Dict, questions: List[Dict]) -> int:
    """Calculate score based on picks vs results"""
    if not results:
        return 0
    
    score = 0
    base_points = 5  # Default points per question
    
    for question in questions:
        q_key = question['key']
        q_type = question['type']
        
        if q_key not in picks or q_key not in results:
            continue
        
        pick_value = picks[q_key]
        result_value = results[q_key]
        
        if pick_value is None or result_value is None:
            continue
        
        # Handle different question types
        if q_type == 'over_under':
            # For over/under, check if pick matches result (Over/Under)
            if pick_value == result_value:
                score += base_points
        elif q_type == 'yes_no':
            # Yes/No questions
            if str(pick_value).lower() == str(result_value).lower():
                score += base_points
        elif q_type == 'select':
            # Multiple choice
            if str(pick_value).strip().lower() == str(result_value).strip().lower():
                score += base_points
        elif q_type == 'text':
            # Text input - exact match (case insensitive)
            if str(pick_value).strip().lower() == str(result_value).strip().lower():
                score += base_points
        elif q_type == 'number':
            # Number input - exact match
            try:
                if float(pick_value) == float(result_value):
                    score += base_points
            except:
                pass
    
    return score

def create_safe_key(text: str, prefix: str = "") -> str:
    """Create a safe, unique key from text"""
    # Create a hash of the text for uniqueness
    text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
    # Sanitize the text for use in key
    safe_text = re.sub(r'[^a-zA-Z0-9]', '_', text[:30])
    key = f"{prefix}_{safe_text}_{text_hash}" if prefix else f"{safe_text}_{text_hash}"
    return key

def render_question_input(question: Dict, key_prefix: str = ""):
    """Render appropriate input widget for a question"""
    q_key = question['key']
    q_text = question['text']
    q_type = question['type']
    q_options = question['options']
    q_required = question.get('required', True)
    
    full_key = create_safe_key(q_key, key_prefix)
    
    if q_type == 'over_under':
        threshold = q_options[0] if q_options else 0
        return st.selectbox(
            f"{q_text} *" if q_required else q_text,
            ["", "Over", "Under"],
            key=full_key
        )
    elif q_type == 'yes_no':
        return st.selectbox(
            f"{q_text} *" if q_required else q_text,
            ["", "Yes", "No"],
            key=full_key
        )
    elif q_type == 'select':
        options = [""] + q_options
        return st.selectbox(
            f"{q_text} *" if q_required else q_text,
            options,
            key=full_key
        )
    elif q_type == 'number':
        return st.number_input(
            f"{q_text} *" if q_required else q_text,
            min_value=0.0,
            value=0.0,
            step=0.1,
            key=full_key
        )
    else:  # text
        return st.text_input(
            f"{q_text} *" if q_required else q_text,
            key=full_key,
            placeholder="Enter your answer"
        )

def main():
    st.title("🏈 Super Bowl LX Prop Picks")
    st.markdown("---")
    
    # Load questions
    questions = load_questions()
    
    if not questions:
        st.error("Could not load questions from Excel file. Please ensure 'Super Bowl LX Picks.xlsx' is in the same directory.")
        return
    
    # Sidebar for admin (results entry)
    with st.sidebar:
        st.header("⚙️ Admin")
        if st.checkbox("Enter Results (Admin Only)"):
            st.subheader("Enter Actual Results")
            results = load_results()
            
            result_inputs = {}
            for question in questions:
                q_key = question['key']
                q_text = question['text']
                q_type = question['type']
                q_options = question['options']
                
                current_value = results.get(q_key, "")
                safe_key = create_safe_key(q_key, "result")
                
                if q_type == 'over_under':
                    threshold = q_options[0] if q_options else 0
                    result_inputs[q_key] = st.selectbox(
                        q_text,
                        ["", "Over", "Under"],
                        index=0 if not current_value else (1 if current_value == "Over" else 2),
                        key=safe_key
                    )
                elif q_type == 'yes_no':
                    result_inputs[q_key] = st.selectbox(
                        q_text,
                        ["", "Yes", "No"],
                        index=0 if not current_value else (1 if current_value == "Yes" else 2),
                        key=safe_key
                    )
                elif q_type == 'select':
                    options = [""] + q_options
                    try:
                        idx = options.index(current_value) if current_value else 0
                    except:
                        idx = 0
                    result_inputs[q_key] = st.selectbox(
                        q_text,
                        options,
                        index=idx,
                        key=safe_key
                    )
                elif q_type == 'number':
                    result_inputs[q_key] = st.number_input(
                        q_text,
                        min_value=0.0,
                        value=float(current_value) if current_value else 0.0,
                        step=0.1,
                        key=safe_key
                    )
                else:  # text
                    result_inputs[q_key] = st.text_input(
                        q_text,
                        value=current_value if current_value else "",
                        key=safe_key
                    )
            
            if st.button("Save Results"):
                # Clean up empty values
                cleaned_results = {k: v if v != "" else None for k, v in result_inputs.items()}
                cleaned_results['updated_at'] = datetime.now().isoformat()
                save_results(cleaned_results)
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
            with col2:
                email = st.text_input("Email *", placeholder="your.email@example.com")
            
            st.markdown("### Prop Questions")
            st.markdown("Please answer all questions. Questions marked with * are required.")
            
            # Group questions into sections for better organization
            game_questions = [q for q in questions if any(word in q['text'].lower() for word in ['game', 'points', 'coin', 'play', 'touchdown', 'turnover', 'penalty', 'field goal', 'conversion', 'pass', 'run', 'tackle', 'reception', 'rushing', 'passing', 'jersey'])]
            commercial_questions = [q for q in questions if 'commercial' in q['text'].lower()]
            halftime_questions = [q for q in questions if any(word in q['text'].lower() for word in ['halftime', 'kendrick', 'lamar', 'song'])]
            anthem_questions = [q for q in questions if 'anthem' in q['text'].lower()]
            other_questions = [q for q in questions if q not in game_questions and q not in commercial_questions and q not in halftime_questions and q not in anthem_questions]
            
            pick_inputs = {}
            
            if game_questions:
                st.markdown("#### 🏈 Game Props")
                for question in game_questions:
                    pick_inputs[question['key']] = render_question_input(question, "pick")
            
            if anthem_questions:
                st.markdown("#### 🎤 National Anthem Props")
                for question in anthem_questions:
                    pick_inputs[question['key']] = render_question_input(question, "pick")
            
            if commercial_questions:
                st.markdown("#### 📺 Commercial Props")
                for question in commercial_questions:
                    pick_inputs[question['key']] = render_question_input(question, "pick")
            
            if halftime_questions:
                st.markdown("#### 🎵 Halftime Show Props")
                for question in halftime_questions:
                    pick_inputs[question['key']] = render_question_input(question, "pick")
            
            if other_questions:
                st.markdown("#### 📋 Other Props")
                for question in other_questions:
                    pick_inputs[question['key']] = render_question_input(question, "pick")
            
            submitted = st.form_submit_button("Submit Picks", type="primary")
            
            if submitted:
                if not name or not email:
                    st.error("Please fill in your name and email!")
                else:
                    # Check required fields
                    required_missing = []
                    for question in questions:
                        if question.get('required', True):
                            q_key = question['key']
                            if not pick_inputs.get(q_key) or pick_inputs[q_key] == "":
                                required_missing.append(question['text'])
                    
                    if required_missing:
                        st.error(f"Please fill in all required fields: {', '.join(required_missing[:3])}{'...' if len(required_missing) > 3 else ''}")
                    else:
                        picks = load_picks()
                        
                        # Check if email already exists
                        if any(p['email'].lower() == email.lower() for p in picks):
                            st.error("This email has already submitted picks!")
                        else:
                            # Clean up empty values
                            cleaned_picks = {k: v if v != "" else None for k, v in pick_inputs.items()}
                            
                            new_pick = {
                                'name': name,
                                'email': email.lower(),
                                **cleaned_picks,
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
                score = calculate_score(pick, results, questions)
                leaderboard_data.append({
                    'Name': pick['name'],
                    'Score': score,
                    'Email': pick.get('email', 'N/A')
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
            
            # Display without email for privacy
            display_df = df[['Rank', 'Name', 'Score']].copy()
            
            st.dataframe(
                display_df.style.apply(
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
                    # Display picks in organized sections
                    pick_items = {k: v for k, v in pick.items() if k not in ['name', 'email', 'submitted_at']}
                    
                    cols = st.columns(2)
                    col_idx = 0
                    for q_key, q_value in pick_items.items():
                        if q_value is not None:
                            question = next((q for q in questions if q['key'] == q_key), None)
                            if question:
                                with cols[col_idx % 2]:
                                    st.write(f"**{question['text']}**")
                                    st.write(f"{q_value}")
                                col_idx += 1
                    
                    if results:
                        score = calculate_score(pick, results, questions)
                        st.metric("Current Score", f"{score} points")

if __name__ == "__main__":
    main()
