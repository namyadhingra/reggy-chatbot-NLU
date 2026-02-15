# streamlit_app.py
# Run with: streamlit run streamlit_app.py

import streamlit as st
import time
import re
from datetime import date, datetime

# =========================================================
# 🎨 PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Reggy++",
    page_icon="🎭",
    layout="centered"
)

# =========================================================
# 🎨 CUSTOM PASTEL + REGENCY CSS
# =========================================================

st.markdown("""
<style>
body {
    background-color: #fdf6f9;
}

.stApp {
    background-image: url("https://images.unsplash.com/photo-1523419409543-a33b51d0b3d8");
    background-size: cover;
    background-attachment: fixed;
}

h1, h2, h3 {
    color: #5c5470;
}

div[data-testid="stChatMessage"] {
    background-color: rgba(255, 240, 245, 0.85);
    border-radius: 15px;
    padding: 10px;
    margin-bottom: 10px;
}

.stButton>button {
    background-color: #e6b7c1;
    color: white;
    border-radius: 10px;
}

.stDownloadButton>button {
    background-color: #cdb4db;
    color: white;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# 📅 DATE PATTERNS
# =========================================================

date_patterns = [
    re.compile(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})'),
    re.compile(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})'),
    re.compile(r'(\d{1,2})[-/](\d{1,2})[-/](\d{2})'),
    re.compile(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})'),
    re.compile(r'([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})')
]

# =========================================================
# 😊 MOOD PATTERNS
# =========================================================

mood_patterns = [
    re.compile(r'\b(hap+y|hap+i+e|glad|goo+d+|gu+d+|joy(?:ful)?|awe?sum|awesome|great|amazing|ama(?:zing))\b', re.IGNORECASE),
    re.compile(r'\b(sad|devasta*ted+|depr+e+s+s?ed+|down|blue|miserable|up+s+e+t+|ba+d)\b', re.IGNORECASE),
    re.compile(r'\b(angr[yi]|mad|furious|ir+itat+ed|frustrat+ed|annoy+ed)\b', re.IGNORECASE),
    re.compile(r'\b(ti+r+ed|exhaus+te+d|slee+py|fatigued|drain+ed)\b', re.IGNORECASE),
    re.compile(r'\b(o+k+a+y+|o*k+|a+l+r+i+g+h+t+|f+i+n+e+|m+e+h+|not\s+ba+d+|do+i+n+g+\s+o+k+a+y+)\b', re.IGNORECASE)
]

# =========================================================
# 🚫 NEGATION PATTERN
# =========================================================

negation_pattern = re.compile(
    r"\b(not|dont|don't|didnt|didn't|never|no)\b",
    re.IGNORECASE
)

# =========================================================
# ReggyPlusPlus CLASS 
# =========================================================
class ReggyPlusPlus:
    # initialier yayay
    def __init__(self):
        self.date_patterns = date_patterns
        # we need conversation state to track what we've asked about, very much needed
        self.user_birthday = None
        self.user_mood = None
        self.user_name = None
        self.user_age = None
        self.awaiting = None #added this "pending slot" state to trach which info currently waiting for

        self.month_map = { 'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6, 'July': 7,
                           'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12, 
                           'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'Jun': 6, 'Jul': 7,
                           'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
                           'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6, 'jul': 7,
                           'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12 }
        # added all lowercase variants too
        # hopefully not missing anything out
        self.vault = {} #self vault is for storing any additional info we might want to use later
        # like user's fav colour, hobbiws etc. - can exoand in future iterations

    def calculate_chronology(self, d_str, m_str, y_str):
        # handle string months
        # oif the month is a name, look it up in the map or else, convert to int
        if m_str.isalpha():
            m = self.month_map.get(m_str.capitalize(), 1)
        else:
            m = int(m_str)
            
        d = int(d_str) # dees is the day
        y = int(y_str) # ze year

        #handle 2 digit years
        if y < 100:
            # asuming 2000s if year is less than 26
            # else 1900s
            if y<26:
                y += 2000
            else:
                y += 1900 
            #in short: y += 2000 if y < 26 else 1900          
        try:
            birth_date = date(y, m, d)
            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            # will subtract (today.month, today.day) if today's date is before the birthday in the current year

            return age, birth_date
        except ValueError:
            return None

    def extract_surname(self, name_text):
        """surname extraction that handles trailing spaces and punctuation """
        # Clean the input first
        clean_name = re.sub(r'[^\w\s]', '', name_text).strip()
        parts = clean_name.split()
        
        if len(parts) > 1:
            return parts[-1].capitalize()
        return "Unknown"

    # Core chatbot method that handles conversation flow
    def chat(self, user_input):
        """ Welcome!! Zis is my main conversation loop method. I've used regex pattern matching to:
        1. Detect what user wants to talk about (birthday, mood, name)
        2. Extract relevant information
        3. Respond appropriately based on conversation state
        4. Ask follow-up questions systematically
        """
        user_input_lower = user_input.lower().strip()
        
        # PRIORITY 1: Check if user provided birthday info
        birthday_response = self.process_birthday(user_input)

        # invalid format
        if birthday_response is None and any(char.isdigit() for char in user_input):
            return "Hmm, that date doesn't seem valid. Could you try another format? (e.g., 25/12/1999 or Dec 25, 1999)"
        
        # valid parsed birthday
        if isinstance(birthday_response, tuple):

            age, birth_date = birthday_response
            self.awaiting = None #clear pending slot since we got the info
            self.user_birthday = birth_date
            self.user_age = age
            formatted_birthday = birth_date.strftime("%d %B %Y")

            response = (f"I understand your birthday as {formatted_birthday}. 🎂\n"
                        f"That makes you {age} years old! 🥳💃🎉 ")
            # using the post-response check function "prompt_for_missing_info"
            follow_up = self.prompt_for_missing_info()
            if follow_up:
                response += follow_up
            return response
        
        # PRIORITY 2: Check if user provided mood info
        mood_response = self.process_mood(user_input)
        if mood_response:
            self.awaiting = None #clear pending slot since we got the info
            self.user_mood = mood_response
            mood_msg = self.get_mood_response(mood_response)
            
            response = f"I sense you're feeling {mood_response}! {mood_msg}"
            
            # Ask about information we don't have yet
            follow_up = self.prompt_for_missing_info()
            if follow_up:
                response += follow_up

            return response
        
        # PRIORITY 3: Check if user provided name info
        name_response = self.process_name(user_input)
        if name_response:
            self.awaiting = None
            self.user_name = name_response
            surname = self.extract_surname(user_input)
            response = f"Nice to meet you, {name_response}! I can see your surname is {surname}\n"
            
            follow_up = self.prompt_for_missing_info()
            if follow_up:
                response += follow_up

            return response
        
        # PRIORITY 4: Conversation starters - check for intent keywords
        #if not self.user_birthday and any(word in user_input_lower for word in ['birthday', 'birth', 'date', 'dob', 'born']):
        #    return "Allow me to calculate your age! What is your birthday? (You can try formats like 12/25/1990, 25-Dec-1995, December 25, 1990, etc.) "
        if any(word in user_input_lower for word in ['birthday', 'birth', 'date', 'dob', 'born']):
            return "Allow me to calculate your age! What is your birthday? (You can try formats like 12/25/1990, 25-Dec-1995, December 25, 1990, etc.) "
        
        #if not self.user_mood and any(word in user_input_lower for word in ['mood', 'feeling', 'vibe', 'emotion', 'how are you']):
        #    return "How are you feeling today? Shall we talk about your mood? (happy, sad, tired, excited, etc.) "
        if any(word in user_input_lower for word in ['mood', 'feeling', 'vibe', 'emotion', 'how are you']):
            return "How are you feeling today? Shall we talk about your mood? (happy, sad, tired, excited, etc.) "
        
        #if not self.user_name and re.search(r'\b(my name is|call me|i am)\b', user_input_lower):
        #    return "What is your full name?"
        if re.search(r'\b(my name is|call me|i am)\b', user_input_lower):
            return "What is your full name?"

        
        #if all info collected AND user just greeted again
        #if user_input_lower in ["hi", "hello", "hey", "summary", "yes", "lite"] and \
        if re.search(r'\b(hi+|hel+o+|hey+|summary+|ye+s+|li+t+e+)\b', user_input_lower) and \
        self.user_name and self.user_age is not None and self.user_mood:
            return (f"Ah, I see! You're {self.user_name} "
                    f"({self.user_age} years old), feeling {self.user_mood}. "
                    "I bid you a wonderful day ahead! "
                    "\nIf you wish to update anything, simply tell me!")


        # DEFAULT: Greeting or conversation starter
        return "Greetings, Gentle User. I am your Whistledown-inspired Reggy++! Let us speak of your birthday, how you might be feeling, or your full name - I assure you I am capable of speaking about them all!"

    # Process mood detection with fuzzy matching
    def process_mood(self, user_input):
        """This is my mood processor function khikhikhi, it detects mood from user input using multiple regex patterns that catch:
        - Exact matches (happy, sad)
        - Common misspellings (hapPy, hapy, deppresed)
        - Various mood synonyms
        It reeturns mood category or None if no mood detected
        """
        lowered = user_input.lower()

        has_negation = bool(negation_pattern.search(lowered))

        for i, pattern in enumerate(mood_patterns):
            match = pattern.search(lowered)
            if match:
                # Map pattern index to mood category huihuiii
                mood_categories = ['happy', 'sad', 'angry', 'tired', 'neutral']

                detected_mood = mood_categories[i]

                # KEY FIX INSERTED HERE: handle "not good", "not happy", etc.
                if has_negation and detected_mood == 'happy':
                    return 'sad'

                return detected_mood

        return None
        

    # Generate appropriate mood based responses huihuii
    def get_mood_response(self, mood):
        """
        Provides contextually appropriate responses based on detected mood
        Each response is encouraging and chatbot-like
        """
        responses = {
            'happy': "I am very happy to hear that! Keep spreading that positivity, you will brighten up all rooms you step foot in! ",
            'excited': "Your excitement is contagious! May I know what excites you so? ",
            'sad': "I'm sorry to hear that. Want to talk about it? Things will get better! ",
            'angry': "Take a deep breath. Maybe some fresh air will help? Let me know how I can assist! ",
            'tired': "Time for a quick break maybe? Rest is important! Ensure you take care of yourself, dearest User. ",
            'neutral': "Fair enough! Anything exciting happening today? "
        }
        return responses.get(mood, "I hear you!")

    #Extract full name from input - Lady Whistledown etc.
    def process_name(self, user_input):
        """
        Detects names even if lowercase and cleans them up.
        """
        # alright, this is thoda sa important part since
        # i had to add egex-based intent detection with word boundaries
        # otherwise the chatbot had no idea where words start or end,
        # and it matched eg "feeling very happy" from " i am feeling very happy"
        # the chatbot caugh tmy name as "M Doing Alright" when I said "I'm doing alright"
        # Look for the pattern!!!
        lowered = user_input.lower()

        intent_patterns = [
            r'\bmy name is\b',
            r'\bi am\b',
            r'\bcall me\b',
            r'\bname is\b'
        ]

        # this allow bare name if bot is expecting it
        if self.awaiting == 'name':
            match = re.fullmatch(r'[a-z]+(?:\s+[a-z]+){1,3}', lowered)
            if match:
                self.awaiting = None
                return match.group().title()
            return None

        # if it contains name intent
        if not any (re.search(p, lowered) for p in intent_patterns):
            return None
        
        cleaned = lowered
        # This check ensures we only try to extract a name if the user has indicated they are providing their name
        # reducing false positives from random capitalized words in other contexts.
        for p in intent_patterns:
            cleaned = re.sub(p, '', cleaned) # remove the intent phrase to isolate the name part

        cleaned = cleaned.strip() # remove leading/trailing spaces
        match = re.fullmatch(r'[a-z]+(?:\s+[a-z]+){1,3}', cleaned)
        if match:
            self.awaiting = None
            # .title() converts "namya dhingra" to "Namya Dhingra" automatically
            return match.group().title()
        return None

    def process_birthday(self, user_input):
        for i, pattern in enumerate(self.date_patterns):
            match = pattern.search(user_input)
            if match:
                groups = match.groups()
                try:
                    if i == 0: # yyyy-mm-dd
                        return self.calculate_chronology(groups[2], groups[1], groups[0])
                    elif i == 3: # dd Month YYYY
                        return self.calculate_chronology(groups[0], groups[1], groups[2])
                    elif i == 4: # Month dd, YYYY
                        return self.calculate_chronology(groups[1], groups[0], groups[2])
                    else: # Numeric dd/mm/yyyy or mm/dd/yyyy
                        val1, val2, year = groups
                        # Logic: If the first number > 12, it MUST be the day (DD/MM)
                        if int(val2) > 12:
                            return self.calculate_chronology(val2, val1, year)

                        # If first value > 12, it MUST be DD/MM
                        if int(val1) > 12:
                            return self.calculate_chronology(val1, val2, year)

                        # Otherwise default to DD/MM (Indian standard)
                        return self.calculate_chronology(val1, val2, year)

                except (ValueError, IndexError):
                    continue
        return None
    
    # after running it multiple times, realised need for this function
    # this one ensrues post-response completion check
    def prompt_for_missing_info(self):
        if not self.user_name:
            self.awaiting = 'name' #pending slot = name
            return "What's your full name?"
        if self.user_age is None:
            self.awaiting = 'birthday' #peding slot = birthday
            return "When is your birthday? (any format works!)"
        if not self.user_mood:
            self.awaiting = 'mood' #pending slot=mood
            return "How are you feeling today?"
        return None



# =========================================================
# 🧠 SESSION STATE INIT
# =========================================================

if "bot" not in st.session_state:
    st.session_state.bot = ReggyPlusPlus()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# =========================================================
# 🏰 TITLE
# =========================================================

st.title("🎭 Reggy++")
st.subheader("Your Whistledown-Inspired Conversational Companion")

st.markdown("---")

# =========================================================
# 📊 USER INFO CARD
# =========================================================

bot = st.session_state.bot

if bot.user_name or bot.user_age or bot.user_mood:
    st.markdown("### 📊 Your Profile So Far")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("👤 Name", bot.user_name if bot.user_name else "Unknown")

    with col2:
        st.metric("🎂 Age", bot.user_age if bot.user_age is not None else "Unknown")

    with col3:
        st.metric("💭 Mood", bot.user_mood if bot.user_mood else "Unknown")

    st.markdown("---")

# =========================================================
# 🔄 RESTART BUTTON
# =========================================================

if st.button("🔄 Restart Conversation"):
    st.session_state.bot = ReggyPlusPlus()
    st.session_state.chat_history = []
    st.rerun()

# =========================================================
# 💬 DISPLAY CHAT
# =========================================================

for role, message in st.session_state.chat_history:
    with st.chat_message(role):
        st.markdown(message)

# Initial greeting
if not st.session_state.chat_history:
    greeting = bot.chat("hello")
    st.session_state.chat_history.append(("assistant", greeting))
    with st.chat_message("assistant"):
        st.markdown(greeting)

# =========================================================
# 💬 CHAT INPUT
# =========================================================

user_input = st.chat_input("Speak, dear user...")

if user_input:

    # Store user message
    st.session_state.chat_history.append(("user", user_input))

    # Quit logic
    if re.search(r'\b(qui+t|exi*t|bye+|go*dbye+)\b', user_input.lower()):
        farewell = "Farewell! Refresh or press Restart to converse again. 🎩"
        st.session_state.chat_history.append(("assistant", farewell))
        st.rerun()

    # Typing animation
    with st.chat_message("assistant"):
        placeholder = st.empty()
        typing_text = "Reggy++ is composing a most elegant reply..."
        for i in range(len(typing_text)):
            placeholder.markdown(typing_text[:i+1])
            time.sleep(0.02)

    # Generate response
    response = bot.chat(user_input)

    # Replace typing with actual response
    with st.chat_message("assistant"):
        st.markdown(response)

    st.session_state.chat_history.append(("assistant", response))
    st.rerun()

# =========================================================
# 📜 DOWNLOAD CHAT LOG
# =========================================================

if st.session_state.chat_history:
    log_text = ""
    for role, message in st.session_state.chat_history:
        if role == "user":
            log_text += f"You: {message}\n"
        else:
            log_text += f"Reggy++: {message}\n"

    st.download_button(
        label="📜 Download Chat Log",
        data=log_text,
        file_name="reggy_chat_log.txt",
        mime="text/plain"
    )

# =========================================================
# 💡 FOOTER NOTE
# =========================================================

st.markdown("---")
st.markdown("""
💡 **Note:**  
If the bot replies in an unexpected way or something feels incorrect,  
simply type **"quit"** or **"exit"** and begin again.

May your society conversations remain ever dramatic. 🎀
""")
