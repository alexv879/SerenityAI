"""
Audio Entertainment System - Pure joy through voice and sound

Entertainment features for elderly users who've never experienced AI:
- Music from their era (1940s-1980s)
- Classic radio shows and dramas
- Voice-activated games and trivia
- Sing-alongs and karaoke
- Audio storytelling with sound effects
- Celebrity voice impressions

NO HEALTH/MEDICAL FEATURES - Pure entertainment only!

Author: Claude Code
Date: 2025-11-18
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import random

logger = logging.getLogger(__name__)


class AudioEntertainment:
    """
    Manages all audio entertainment features

    Features:
    - Music requests from their era
    - Audio games and trivia
    - Interactive storytelling
    - Sing-alongs
    - Radio show style content
    """

    def __init__(self, redis_client=None):
        """
        Initialize audio entertainment system

        Args:
            redis_client: Redis client for preferences and scores
        """
        self.redis_client = redis_client

    async def play_music_from_era(
        self,
        user_id: str,
        decade: Optional[str] = None,
        genre: Optional[str] = None,
        artist: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Play music from user's era

        Args:
            user_id: User's phone number
            decade: "1940s", "1950s", "1960s", "1970s", "1980s"
            genre: "swing", "rock_and_roll", "jazz", "classical", "folk"
            artist: Specific artist request

        Returns:
            Music selection and playback instructions
        """
        # Popular artists by decade
        music_catalog = {
            "1940s": {
                "artists": ["Vera Lynn", "Frank Sinatra", "Bing Crosby", "Glenn Miller"],
                "genres": ["swing", "jazz", "big_band"],
                "hits": [
                    "We'll Meet Again - Vera Lynn",
                    "White Christmas - Bing Crosby",
                    "In the Mood - Glenn Miller"
                ]
            },
            "1950s": {
                "artists": ["Elvis Presley", "Buddy Holly", "Chuck Berry", "Doris Day"],
                "genres": ["rock_and_roll", "doo_wop", "rockabilly"],
                "hits": [
                    "Hound Dog - Elvis Presley",
                    "That'll Be the Day - Buddy Holly",
                    "Johnny B. Goode - Chuck Berry"
                ]
            },
            "1960s": {
                "artists": ["The Beatles", "The Rolling Stones", "The Beach Boys", "Dusty Springfield"],
                "genres": ["rock", "pop", "motown", "folk"],
                "hits": [
                    "Hey Jude - The Beatles",
                    "(I Can't Get No) Satisfaction - The Rolling Stones",
                    "Good Vibrations - The Beach Boys"
                ]
            },
            "1970s": {
                "artists": ["ABBA", "Elton John", "Queen", "Carpenters"],
                "genres": ["disco", "rock", "pop", "folk"],
                "hits": [
                    "Dancing Queen - ABBA",
                    "Bohemian Rhapsody - Queen",
                    "Your Song - Elton John"
                ]
            },
            "1980s": {
                "artists": ["Michael Jackson", "Madonna", "Whitney Houston", "Wham!"],
                "genres": ["pop", "new_wave", "synth_pop"],
                "hits": [
                    "Billie Jean - Michael Jackson",
                    "Like a Virgin - Madonna",
                    "I Wanna Dance with Somebody - Whitney Houston"
                ]
            }
        }

        # Default to user's likely era (70s/80s for current elderly)
        if not decade:
            decade = "1960s"

        era_data = music_catalog.get(decade, music_catalog["1960s"])

        if artist:
            return {
                "success": True,
                "message": f"Playing music by {artist} from the {decade}. I hope you enjoy this!",
                "decade": decade,
                "artist": artist,
                "instruction": f"Play {artist} music from {decade} era via music service"
            }

        # Pick a random hit from the era
        hit = random.choice(era_data["hits"])

        return {
            "success": True,
            "message": f"Here's a classic from the {decade}: {hit}. This always brings back memories!",
            "song": hit,
            "decade": decade,
            "instruction": f"Play: {hit}"
        }

    async def play_trivia_game(
        self,
        user_id: str,
        category: str = "general"
    ) -> Dict[str, Any]:
        """
        Start an interactive trivia game

        Categories: history, music, films, television, geography

        Returns:
            Trivia question
        """
        trivia_questions = {
            "history": [
                {
                    "question": "In what year did World War II end?",
                    "answer": "1945",
                    "hint": "It was in the mid-1940s",
                    "fun_fact": "VE Day was May 8th, 1945, and VJ Day was August 15th, 1945."
                },
                {
                    "question": "Who was the first person to walk on the moon?",
                    "answer": "Neil Armstrong",
                    "hint": "His first name is Neil",
                    "fun_fact": "It happened on July 20, 1969. What a momentous day that was!"
                }
            ],
            "music": [
                {
                    "question": "Which band sang 'Hey Jude'?",
                    "answer": "The Beatles",
                    "hint": "They were the most famous band from Liverpool",
                    "fun_fact": "Hey Jude was the longest Beatles single at 7 minutes!"
                },
                {
                    "question": "Who was known as 'The King of Rock and Roll'?",
                    "answer": "Elvis Presley",
                    "hint": "His first name is Elvis",
                    "fun_fact": "Elvis had his first hit 'Heartbreak Hotel' in 1956!"
                }
            ],
            "films": [
                {
                    "question": "Who played James Bond in 'Goldfinger'?",
                    "answer": "Sean Connery",
                    "hint": "He was Scottish",
                    "fun_fact": "Goldfinger came out in 1964 and is considered one of the best Bond films!"
                }
            ],
            "television": [
                {
                    "question": "What was the name of Del Boy's brother in 'Only Fools and Horses'?",
                    "answer": "Rodney",
                    "hint": "It rhymes with 'kidney'",
                    "fun_fact": "The show ran for 22 years from 1981 to 2003!"
                }
            ]
        }

        questions = trivia_questions.get(category, trivia_questions["history"])
        question_data = random.choice(questions)

        # Store question for answer checking
        if self.redis_client:
            await self.redis_client.set(
                f"trivia_current:{user_id}",
                json.dumps(question_data),
                ex=300  # 5 minutes
            )

        return {
            "success": True,
            "category": category,
            "question": question_data["question"],
            "message": f"Here's a {category} question for you: {question_data['question']}"
        }

    async def check_trivia_answer(
        self,
        user_id: str,
        user_answer: str
    ) -> Dict[str, Any]:
        """
        Check if user's trivia answer is correct

        Returns:
            Result with encouragement
        """
        if not self.redis_client:
            return {
                "success": False,
                "message": "I can't check that right now, but I bet you got it right!"
            }

        # Get stored question
        question_json = await self.redis_client.get(f"trivia_current:{user_id}")
        if not question_json:
            return {
                "success": False,
                "message": "I don't remember what question I asked! Shall we try another one?"
            }

        if isinstance(question_json, bytes):
            question_json = question_json.decode('utf-8')

        question_data = json.loads(question_json)
        correct_answer = question_data["answer"].lower()

        # Check answer (fuzzy matching)
        is_correct = correct_answer in user_answer.lower() or user_answer.lower() in correct_answer

        if is_correct:
            # Update score
            score_key = f"trivia_score:{user_id}"
            score = await self.redis_client.incr(score_key)
            await self.redis_client.expire(score_key, 30 * 24 * 60 * 60)  # 30 days

            return {
                "success": True,
                "correct": True,
                "message": f"That's absolutely right! Well done! {question_data['fun_fact']} Your score is now {score}!",
                "score": score,
                "fun_fact": question_data["fun_fact"]
            }
        else:
            return {
                "success": True,
                "correct": False,
                "message": f"Oh, I'm afraid not. The answer was {question_data['answer']}. {question_data['fun_fact']} Shall we try another question?",
                "correct_answer": question_data["answer"],
                "fun_fact": question_data["fun_fact"]
            }

    async def tell_interactive_story(
        self,
        user_id: str,
        story_type: str = "mystery"
    ) -> Dict[str, Any]:
        """
        Start an interactive choose-your-own-adventure story

        Story types: mystery, adventure, romance, comedy

        Returns:
            Story opening with choices
        """
        stories = {
            "mystery": {
                "title": "The Case of the Missing Teacup",
                "opening": (
                    "You're visiting your friend Agatha for afternoon tea, but when you arrive, "
                    "her prized Royal Albert teacup is missing! She's terribly upset. "
                    "You notice the window is open and there are muddy footprints by the door. "
                    "What would you like to do? Check the footprints, or look out the window?"
                ),
                "choices": ["Check the footprints", "Look out the window"]
            },
            "adventure": {
                "title": "The Treasure in the Attic",
                "opening": (
                    "You're helping your grandchildren clean out the attic when you discover "
                    "an old map in a dusty trunk. It shows a path through your garden leading "
                    "to an 'X' marked near the old oak tree! Do you want to follow the map "
                    "right away, or examine the trunk for more clues?"
                ),
                "choices": ["Follow the map", "Examine the trunk"]
            }
        }

        story_data = stories.get(story_type, stories["mystery"])

        # Store story state
        if self.redis_client:
            state = {
                "type": story_type,
                "stage": "opening",
                "title": story_data["title"]
            }
            await self.redis_client.set(
                f"story_state:{user_id}",
                json.dumps(state),
                ex=3600  # 1 hour
            )

        choices_str = " or ".join(story_data["choices"])

        return {
            "success": True,
            "story_type": story_type,
            "title": story_data["title"],
            "message": f"{story_data['title']}. {story_data['opening']}",
            "choices": story_data["choices"]
        }

    async def create_singalong_session(
        self,
        user_id: str,
        song_type: str = "classic"
    ) -> Dict[str, Any]:
        """
        Start a singalong session with lyrics

        Song types: classic, wartime, christmas, folk

        Returns:
            Song lyrics for singalong
        """
        singalong_songs = {
            "classic": [
                {
                    "title": "Daisy Bell (A Bicycle Built for Two)",
                    "lyrics": (
                        "Daisy, Daisy, give me your answer do,\n"
                        "I'm half crazy, all for the love of you!\n"
                        "It won't be a stylish marriage,\n"
                        "I can't afford a carriage,\n"
                        "But you'll look sweet upon the seat,\n"
                        "Of a bicycle built for two!"
                    )
                }
            ],
            "wartime": [
                {
                    "title": "We'll Meet Again",
                    "lyrics": (
                        "We'll meet again, don't know where, don't know when,\n"
                        "But I know we'll meet again some sunny day!\n"
                        "Keep smiling through, just like you always do,\n"
                        "Till the blue skies drive the dark clouds far away!"
                    )
                }
            ],
            "folk": [
                {
                    "title": "Scarborough Fair",
                    "lyrics": (
                        "Are you going to Scarborough Fair?\n"
                        "Parsley, sage, rosemary, and thyme,\n"
                        "Remember me to one who lives there,\n"
                        "She once was a true love of mine."
                    )
                }
            ]
        }

        songs = singalong_songs.get(song_type, singalong_songs["classic"])
        song = random.choice(songs)

        return {
            "success": True,
            "song_title": song["title"],
            "message": f"Let's sing {song['title']} together! I'll start us off, and you join in when you're ready.",
            "lyrics": song["lyrics"],
            "instruction": f"Read lyrics slowly with musical tone: {song['lyrics']}"
        }

    async def play_word_game(
        self,
        user_id: str,
        game_type: str = "rhyme"
    ) -> Dict[str, Any]:
        """
        Play interactive word games

        Game types: rhyme, riddle, memory, association

        Returns:
            Game prompt
        """
        games = {
            "rhyme": {
                "name": "Rhyme Time",
                "prompt": "I'll say a word, and you say a word that rhymes with it. Ready? Here we go: CAT",
                "instruction": "Listen for user's rhyme attempt and respond encouragingly"
            },
            "riddle": {
                "name": "Classic Riddles",
                "prompts": [
                    "I have hands but cannot clap. What am I? (Answer: A clock)",
                    "What has keys but no locks, space but no room, and you can enter but can't go inside? (Answer: A keyboard)",
                    "The more you take, the more you leave behind. What am I? (Answer: Footsteps)"
                ]
            },
            "memory": {
                "name": "Memory Game",
                "prompt": "I'll name three things, and you repeat them back. Ready? Apple, Garden, Sunshine",
                "items": ["Apple", "Garden", "Sunshine"]
            }
        }

        game = games.get(game_type, games["rhyme"])

        if game_type == "riddle":
            riddle = random.choice(game["prompts"])
            return {
                "success": True,
                "game": game["name"],
                "message": f"Here's a riddle for you: {riddle.split('(Answer:')[0]}",
                "answer": riddle.split('(Answer:')[1].strip(')') if '(Answer:' in riddle else None
            }

        return {
            "success": True,
            "game": game["name"],
            "message": game["prompt"]
        }


# Global singleton
_audio_entertainment: Optional[AudioEntertainment] = None
_entertainment_lock = asyncio.Lock()


async def get_audio_entertainment(redis_client=None) -> AudioEntertainment:
    """Get or create audio entertainment singleton"""
    global _audio_entertainment
    if _audio_entertainment is None:
        async with _entertainment_lock:
            if _audio_entertainment is None:
                _audio_entertainment = AudioEntertainment(redis_client)
    return _audio_entertainment
