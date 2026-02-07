import streamlit as st
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import pandas as pd
import re
import hashlib
from zoneinfo import ZoneInfo

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
QUESTIONS_TXT_FILE = "questions.txt"
QUESTION_CONFIG_FILE = "question_config.json"

# Initialize session state
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "questions" not in st.session_state:
    st.session_state.questions = None

def load_question_config() -> Dict:
    """Load question configuration from JSON file"""
    if os.path.exists(QUESTION_CONFIG_FILE):
        with open(QUESTION_CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def parse_questions_txt() -> List[Dict]:
    """Parse questions from questions.txt file (Google Forms export format)"""
    if not os.path.exists(QUESTIONS_TXT_FILE):
        return []
    
    questions = []
    exclude_questions = [
        'Email',
        'Name',
        'Would you like to opt-in for $20 SUPER BOWL POOL',
        'Did you Venmo $20',
        'For auditing purposes, what is your Venmo handle',
        'If you win, what is your charity of choice'
    ]
    
    with open(QUESTIONS_TXT_FILE, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines()]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Skip header/metadata lines
        if not line or line.startswith('Screen reader') or line.startswith('Super Bowl LX') or line.startswith('$20 Entry') or line.startswith('This form') or line.startswith('Banner') or line == '.':
            i += 1
            continue
        
        # Check if this looks like a question (not an answer option)
        # Questions typically don't start with common answer patterns
        if line and not line.startswith('*') and line not in ['Over', 'Under', 'Yes', 'No', 'Heads', 'Tails', 'Even', 'Odd', 'Up', 'Down']:
            question_text = line
            required = False
            options = []
            
            # Check if next line is * (required indicator)
            if i + 1 < len(lines) and lines[i + 1] == '*':
                required = True
                i += 2  # Skip question and *
            else:
                i += 1  # Skip just the question
            
            # Skip if this is an excluded question
            if any(exc.lower() in question_text.lower() for exc in exclude_questions):
                # Skip to next question (until we hit a line that looks like a question)
                while i < len(lines) and (lines[i] in ['Over', 'Under', 'Yes', 'No', 'Heads', 'Tails', 'Even', 'Odd', 'Up', 'Down'] or lines[i].startswith('*') or not lines[i]):
                    i += 1
                continue
            
            # Collect answer options until we hit next question or empty line
            while i < len(lines):
                if not lines[i]:  # Empty line means end of options
                    i += 1
                    break
                
                # Check if this looks like a new question (has question mark or starts with question words)
                looks_like_question = (
                    '?' in lines[i] or
                    lines[i].startswith(('Who ', 'What ', 'Which ', 'Will ', 'How ', 'When ', 'Where ', 'Why ')) or
                    lines[i].startswith(('Seattle ', 'Total ', 'National ', 'First ', 'More ', 'Number ', 'Color ', 'Bad ', 'A commercial', 'From kick-off'))
                )
                
                # If it looks like a question and we already have options, this is a new question
                if looks_like_question and len(options) > 0:
                    break
                
                # If it's a common answer option, collect it
                if lines[i] in ['Over', 'Under', 'Yes', 'No', 'Heads', 'Tails', 'Even', 'Odd', 'Up', 'Down', 'Run', 'Pass/Sack', 'Fumble', 'Interception', 'Turnover on Downs']:
                    if lines[i] != '*':
                        options.append(lines[i])
                    i += 1
                    continue
                
                # If it doesn't look like a question, it's an option
                if not looks_like_question:
                    if lines[i] != '*':
                        options.append(lines[i])
                    i += 1
                else:
                    # It looks like a question but we don't have options yet - might be the first question
                    # or might be an option that happens to look like a question
                    # If we're collecting options, treat it as an option unless it has a question mark
                    if len(options) == 0 and '?' in lines[i]:
                        # This is actually a new question
                        break
                    else:
                        # Treat as option
                        if lines[i] != '*':
                            options.append(lines[i])
                        i += 1
            
            # Determine question type based on options
            if not options:
                # No options = text or number input
                if 'TIE BREAKER' in question_text.upper() or 'Total Points Scored' in question_text:
                    q_type = 'number'
                    q_options = []
                else:
                    q_type = 'text'
                    q_options = []
            elif len(options) == 2 and set(options) == {'Over', 'Under'}:
                # Over/Under question
                # Extract threshold from question text
                match = re.search(r'over/under\s+([\d.]+)', question_text.lower())
                threshold = float(match.group(1)) if match else 0
                q_type = 'over_under'
                q_options = [threshold]
            elif len(options) == 2 and set(options) == {'Yes', 'No'}:
                q_type = 'yes_no'
                q_options = []
            elif len(options) > 0:
                q_type = 'select'
                q_options = options
            else:
                q_type = 'text'
                q_options = []
            
            questions.append({
                'key': question_text,
                'text': question_text,
                'type': q_type,
                'options': q_options,
                'required': required
            })
        else:
            i += 1
    
    return questions

def load_questions() -> List[Dict]:
    """Load questions from questions.txt file (preferred) or Excel file"""
    if st.session_state.questions is not None:
        return st.session_state.questions
    
    try:
        # Try to load from questions.txt first
        questions = parse_questions_txt()
        
        if questions:
            st.session_state.questions = questions
            return questions
        
        # Fall back to Excel file if questions.txt doesn't exist or is empty
        df = pd.read_excel(QUESTIONS_FILE)
        config = load_question_config()
        
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
                # Check if question is in config file first
                if col in config:
                    q_config = config[col]
                    q_type = q_config.get('type', 'text')
                    if q_type == 'over_under':
                        options = [q_config.get('threshold', 0)]
                    else:
                        options = q_config.get('options', [])
                else:
                    # Fall back to automatic detection
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
    
    # Game spread question (first question about which team covers)
    # Check for game spread question - must have both teams and a vs/@ indicator
    if ('seahawks' in q_lower and 'patriots' in q_lower and 
        ('vs' in q_lower or '@' in question_text)):
        return 'select', ['Seahawks -4.5', 'Patriots +4.5']
    
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

def export_picks_to_excel(picks: List[Dict], filename: str = "picks_export.xlsx"):
    """Export all picks to Excel file with name and email"""
    if not picks:
        return None
    
    # Create a list of dictionaries for the DataFrame
    export_data = []
    for pick in picks:
        row = {
            'Name': pick.get('name', ''),
            'Email': pick.get('email', ''),
            'Playing for Money': pick.get('playing_for_money', ''),
            'Submitted At': pick.get('submitted_at', '')
        }
        
        # Add all question answers
        for key, value in pick.items():
            if key not in ['name', 'email', 'playing_for_money', 'submitted_at']:
                row[key] = value if value is not None else ''
        
        export_data.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(export_data)
    
    # Export to Excel
    df.to_excel(filename, index=False, engine='openpyxl')
    return filename

def can_view_picks() -> bool:
    """Check if current time is after 6pm EST on Sunday 2/8/2026"""
    try:
        est = ZoneInfo("America/New_York")
    except:
        # Fallback for systems without zoneinfo
        from datetime import timedelta
        est_offset = timedelta(hours=-5)  # EST is UTC-5
        est = timezone(est_offset)
    
    now = datetime.now(est)
    
    # Target: 6pm EST on Sunday, February 8, 2026
    target = datetime(2026, 2, 8, 18, 0, 0, tzinfo=est)
    
    return now >= target

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

def create_safe_key(text: str, prefix: str = "", index: int = None) -> str:
    """Create a safe, unique key from text"""
    # Create a hash of the text for uniqueness
    text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
    # Sanitize the text for use in key
    safe_text = re.sub(r'[^a-zA-Z0-9]', '_', text[:30])
    # Include index if provided for extra uniqueness
    if index is not None:
        key = f"{prefix}_{index}_{safe_text}_{text_hash}" if prefix else f"{index}_{safe_text}_{text_hash}"
    else:
        key = f"{prefix}_{safe_text}_{text_hash}" if prefix else f"{safe_text}_{text_hash}"
    return key

def render_question_input(question: Dict, key_prefix: str = "", index: int = None):
    """Render appropriate input widget for a question"""
    q_key = question['key']
    q_text = question['text']
    q_type = question['type']
    q_options = question['options']
    q_required = question.get('required', True)
    
    full_key = create_safe_key(q_key, key_prefix, index)
    
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
        admin_password = st.text_input("Admin Password", type="password", key="admin_password")
        admin_authenticated = (admin_password == "Pr0pP!cks")
        
        if admin_authenticated:
            st.subheader("Admin Tools")
            
            # Export picks to Excel
            picks = load_picks()
            if picks:
                if st.button("📥 Export All Picks to Excel"):
                    filename = export_picks_to_excel(picks, "picks_export.xlsx")
                    if filename and os.path.exists(filename):
                        with open(filename, 'rb') as f:
                            st.download_button(
                                label="Download Excel File",
                                data=f.read(),
                                file_name=filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        st.success(f"Exported {len(picks)} picks to Excel!")
            
            if st.checkbox("Enter Results (Admin Only)"):
                st.subheader("Enter Actual Results")
                results = load_results()
                
                result_inputs = {}
                for idx, question in enumerate(questions):
                    q_key = question['key']
                    q_text = question['text']
                    q_type = question['type']
                    q_options = question['options']
                    
                    current_value = results.get(q_key, "")
                    safe_key = create_safe_key(q_key, "result", idx)
                    
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
        else:
            if admin_password:
                st.error("Incorrect password")
    
    # Main tabs - conditionally show "All Picks" tab
    if can_view_picks():
        tab1, tab2, tab3 = st.tabs(["📝 Submit Picks", "📊 Leaderboard", "📋 All Picks"])
    else:
        tab1, tab2 = st.tabs(["📝 Submit Picks", "📊 Leaderboard"])
        tab3 = None
    
    with tab1:
        st.header("Submit Your Prop Picks")
        
        # Instructions
        st.info("""
        **$20 Entry** - Half of winnings to Charity of Winner's choice and other half in their pocket. 
        Must submit picks by 02/08 before National Anthem start. 
        If you want to change your picks, we will accept latest entries. 
        Please Venmo **tim-roberts-16**
        
        *Note: You're welcome to play for fun, but we encourage you to join the pool to help support charity!*
        """)
        
        with st.form("picks_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Your Name *", placeholder="Enter your name")
            with col2:
                email = st.text_input("Email *", placeholder="your.email@example.com")
            
            # Playing for money question
            playing_for_money = st.selectbox(
                "Are you playing for money? *",
                ["", "Yes, I'm in the $20 pool", "No, just playing for fun"],
                help="Select whether you're participating in the $20 charity pool or just playing for fun"
            )
            
            st.markdown("### Prop Questions")
            st.markdown("Please answer all questions. Questions marked with * are required.")
            
            # Group questions into sections for better organization
            # Use sets to track which questions have been added to avoid duplicates
            added_questions = set()
            game_questions = []
            commercial_questions = []
            halftime_questions = []
            anthem_questions = []
            other_questions = []
            
            # Categorize questions, ensuring no duplicates
            for q in questions:
                q_key = q['key']
                if q_key in added_questions:
                    continue
                
                q_lower = q['text'].lower()
                if any(word in q_lower for word in ['game', 'points', 'coin', 'play', 'touchdown', 'turnover', 'penalty', 'field goal', 'conversion', 'pass', 'run', 'tackle', 'reception', 'rushing', 'passing', 'jersey']):
                    game_questions.append(q)
                    added_questions.add(q_key)
                elif 'commercial' in q_lower:
                    commercial_questions.append(q)
                    added_questions.add(q_key)
                elif any(word in q_lower for word in ['halftime', 'kendrick', 'lamar', 'song']):
                    halftime_questions.append(q)
                    added_questions.add(q_key)
                elif 'anthem' in q_lower:
                    anthem_questions.append(q)
                    added_questions.add(q_key)
                else:
                    other_questions.append(q)
                    added_questions.add(q_key)
            
            pick_inputs = {}
            question_index = 0
            
            if game_questions:
                st.markdown("#### 🏈 Game Props")
                for question in game_questions:
                    pick_inputs[question['key']] = render_question_input(question, "pick", question_index)
                    question_index += 1
            
            if anthem_questions:
                st.markdown("#### 🎤 National Anthem Props")
                for question in anthem_questions:
                    pick_inputs[question['key']] = render_question_input(question, "pick", question_index)
                    question_index += 1
            
            if commercial_questions:
                st.markdown("#### 📺 Commercial Props")
                for question in commercial_questions:
                    pick_inputs[question['key']] = render_question_input(question, "pick", question_index)
                    question_index += 1
            
            if halftime_questions:
                st.markdown("#### 🎵 Halftime Show Props")
                for question in halftime_questions:
                    pick_inputs[question['key']] = render_question_input(question, "pick", question_index)
                    question_index += 1
            
            if other_questions:
                st.markdown("#### 📋 Other Props")
                for question in other_questions:
                    pick_inputs[question['key']] = render_question_input(question, "pick", question_index)
                    question_index += 1
            
            submitted = st.form_submit_button("Submit Picks", type="primary")
            
            if submitted:
                if not name or not email:
                    st.error("Please fill in your name and email!")
                elif not playing_for_money:
                    st.error("Please indicate if you're playing for money or just for fun!")
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
                                'playing_for_money': playing_for_money if playing_for_money else None,
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
    
    if tab3:
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
                        pick_items = {k: v for k, v in pick.items() if k not in ['name', 'email', 'submitted_at', 'playing_for_money']}
                        
                        # Show playing for money status
                        if pick.get('playing_for_money'):
                            st.write(f"**Playing for Money:** {pick['playing_for_money']}")
                            st.markdown("---")
                        
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
    else:
        # Show message if picks are locked
        st.info("🔒 Picks will be visible after 6pm EST on Sunday, February 8th, 2026")

if __name__ == "__main__":
    main()
