"""
Story Library for Serenity AI
Classic British stories, nostalgia tales, and gentle entertainment
Focused on 1940s-1960s era for elderly demographic
"""

import random
from typing import Dict, List

# Story database organized by theme
STORIES = {
    "classic": [
        {
            "title": "The Village Garden Competition",
            "length": "medium",
            "content": """
It was the summer of 1958, and the entire village was buzzing with excitement about the annual garden competition. 
Mrs. Thompson had won for three years running with her prize roses, but this year, newcomer Mr. Jenkins had been 
tending to the most magnificent display of dahlias anyone had ever seen.

The morning of the judging, Mrs. Thompson discovered that her best rose bush had been nibbled by rabbits overnight. 
She was devastated. But Mr. Jenkins, seeing her distress, quietly snipped some of his finest dahlias and helped 
her arrange them alongside her remaining roses.

When the judges arrived, they were so moved by the beautiful combination and the story of neighborly kindness 
that they declared it a tie. The two gardeners shared the blue ribbon, and Mrs. Thompson invited Mr. Jenkins 
for tea every Sunday thereafter.

As my grandmother used to say, the best gardens grow friendships as well as flowers.
            """,
            "delivery_notes": "Warm, nostalgic tone. Emphasize the kindness and community spirit. Pause after 'nibbled by rabbits' for dramatic effect."
        },
        {
            "title": "The Postman's Secret",
            "length": "short",
            "content": """
In our village, everyone knew Mr. Davies the postman. For forty years, he'd walked the same route, rain or shine, 
delivering letters and parcels with a cheerful whistle.

What most people didn't know was that Mr. Davies could barely read. He'd left school at twelve to help on his 
father's farm. But he'd memorized every house, every family, every person's handwriting. He knew Mrs. Parker 
always got letters from Australia on Thursdays, and young Tommy's birthday cards arrived in February.

When he finally retired, the whole village turned out. The vicar gave a speech, but it was little Lucy, 
aged seven, who said it best: "Mr. Davies knew what mattered - not the words on the letters, but the love inside them."

There wasn't a dry eye in the village hall that day.
            """,
            "delivery_notes": "Start with gentle warmth, build emotional depth at the revelation. Deliver Lucy's line with childlike clarity. End with quiet reverence."
        }
    ],
    
    "nostalgia": [
        {
            "title": "The Sweet Shop Window",
            "length": "short",
            "content": """
Do you remember the sweet shops? Not the modern ones, but the proper sweet shops with glass jars lining the walls?

I remember standing outside Barker's Sweet Shop on Market Street, pressing my nose against the window. 
Rows and rows of glass jars: sherbet lemons, liquorice allsorts, aniseed balls, pear drops. 
Each one cost a ha'penny, and on Saturdays, my mother would give me threepence to spend.

The bell above the door would ting-a-ling as you entered. Mrs. Barker, with her flour-white hair and 
spectacles on a chain, would smile and say "Now then, what'll it be today?"

I'd stand there for what felt like hours, deliberating. Finally, I'd choose - usually a quarter of bonbons 
and a sherbet fountain. Mrs. Barker would weigh them on her brass scales, tip them into a little paper bag, 
and twist the corners just so.

Those sweets tasted like pure joy. Maybe it was the sugar. Or maybe it was being eight years old on a sunny Saturday morning.
            """,
            "delivery_notes": "Dreamy, wistful tone. Linger on the details - the ting-a-ling, the brass scales. Let the listener taste the memory."
        },
        {
            "title": "Wireless Nights",
            "length": "medium",
            "content": """
Before television ruled our evenings, we had the wireless. 

Sunday nights, the whole family would gather in the front room. Father in his armchair, Mother darning socks, 
my brother and I sprawled on the rug in front of the fire. The wireless sat in pride of place on the sideboard, 
its warm amber dial glowing like a promise.

Six o'clock meant The Archers. Half past seven was our favorite - Journey into Space. We'd turn off all the 
lights and let our imaginations soar with Jet Morgan and his crew. When the Martians attacked, I'd grab 
my brother's hand, my heart racing.

Mother would make cocoa in the interval, and we'd dunk our biscuits while discussing whether Jet would 
make it back to Earth this time. Father would pretend he wasn't as gripped as we were, but I noticed 
he never got up during the program.

We didn't need pictures. The pictures were in our heads, and they were magnificent. The rustle of the 
spacecraft door, the echo of alien caves, Jet's steady voice - "It's all right, everyone. We'll get through this."

Those were the nights when our little front room became the entire universe.
            """,
            "delivery_notes": "Begin with gentle nostalgia, build excitement during the program description. Use sound effects - emphasize 'rustled', 'echo'. End with cozy warmth."
        }
    ],
    
    "wartime": [
        {
            "title": "The Victory Street Party",
            "length": "medium",
            "content": """
The eighth of May, 1945. VE Day. The war in Europe was over.

Our street had survived. Oh, we'd had some close calls - Mr. Peterson's house had lost its roof in the Blitz, 
and we'd all spent countless nights in the Anderson shelter. But we'd survived, and now, incredibly, 
it was over.

Someone found a Union Jack that hadn't been moth-eaten. Mrs. Collins donated her precious sugar ration 
for cakes. Mr. Harris dragged his piano into the street - don't ask me how. Tables appeared from every 
house, laid end to end down the middle of the road.

The children, who'd grown up knowing only war, ran wild with joy. They didn't quite understand what 
peace meant, but they knew it meant the blackout curtains were coming down forever.

We danced in the street until our feet hurt. Mrs. Davies, who was seventy-eight, kicked her heels higher 
than anyone. My father, who never cried, wept into his tea and no one mentioned it.

At midnight, we all stood together and sang "God Save the King" and "There'll Always Be an England." 
And we believed it, because we'd proved it. We were still standing.

That night, London blazed with light for the first time in six years. And it was the most beautiful thing any of us had ever seen.
            """,
            "delivery_notes": "Start subdued, build to joyous celebration. Honor the weight of what they'd endured. Deliver the final line with quiet pride and wonder."
        }
    ],
    
    "bedtime": [
        {
            "title": "The Lighthouse Keeper's Cat",
            "length": "medium",
            "content": """
On a rocky point where the sea meets the sky, there stood a lighthouse, and in that lighthouse lived 
Keeper Thomas and his marmalade cat, Barnaby.

Every evening, as the sun painted the waves gold and pink, Keeper Thomas would climb the spiral stairs 
to light the great lamp. Barnaby always followed, his paws padding soft on the iron steps - 
one hundred and forty-two of them, Barnaby had them counted.

At the top, while Keeper Thomas polished the great lens until it sparkled, Barnaby would sit on the 
windowsill and watch the fishing boats come home. He knew each one by name: The Mary Rose, The Silver Dawn, 
The Wanderer. Their lights bobbed on the darkening water like dancing stars.

One stormy night, when the wind howled and the waves crashed high against the rocks, Barnaby noticed 
something. The Mary Rose's light was flickering in an odd pattern. Keeper Thomas was busy with the lamp, 
so Barnaby did the only thing he could - he meowed. Not a regular meow, but a urgent, insistent meow 
that he kept up until Keeper Thomas came to see what the fuss was about.

Through his telescope, Keeper Thomas saw what Barnaby had spotted - The Mary Rose had lost her rudder 
and was drifting toward the rocks. He immediately radioed the lifeboat, and within the hour, 
the crew was safe.

The fishermen brought Barnaby a whole cod the next day. Keeper Thomas said Barnaby was too modest 
to make a fuss about being a hero, but between you and me, I think Barnaby knew exactly what he'd done.

And on clear nights, if you visit that lighthouse, you might see a marmalade cat sitting on the windowsill, 
watching over the boats as they come safely home.

Sleep well now. The light is always shining, and Barnaby is on watch.
            """,
            "delivery_notes": "Gentle, soothing rhythm like waves. Slow pacing. Soften voice for 'sleep well now' ending. This is meant to send someone peacefully to sleep."
        }
    ],
    
    "gentle_humor": [
        {
            "title": "The Runaway Teeth",
            "length": "short",
            "content": """
My grandfather loved to tell the story of his friend Albert and the runaway teeth.

Albert had just gotten his first set of false teeth - very proud of them, he was. Gleaming white, 
perfect fit. He wore them to the British Legion on Friday night to show them off.

Now, Albert liked his beer, and after a few pints, he got talking rather animatedly about the cricket. 
He was demonstrating how the bowler had knocked the wicket clean out when his hands flew up in excitement.

His teeth flew up too. Straight up in the air they went, arcing across the room in a perfect parabola. 
The entire pub fell silent, every eye following those pearly whites as they sailed through the air 
and landed - plop! - right in Mrs. Henderson's gin and tonic.

Mrs. Henderson, bless her, didn't bat an eye. She fished out the teeth, walked over to Albert, 
and said, "I believe you've lost something. And I'll have another gin and tonic, if you don't mind."

Albert bought her drinks for the rest of the night. He also got a jar of extra-strong denture adhesive the very next day.

At the Legion, they still call that corner booth "Albert's Launch Pad."
            """,
            "delivery_notes": "Light, amused tone. Build anticipation with the arc of the teeth. Deliver Mrs. Henderson's line with perfect comic timing and British understatement. Chuckle at the ending."
        }
    ]
}

# Jokes database - clean and elderly-appropriate
JOKES = {
    "gentle": [
        "I told my doctor I heard buzzing, but it was just my grandson's computer. He said 'That's not an illness, that's progress!",
        "I asked my granddaughter to show me how to use 'the cloud.' She pointed out the window. I said 'No dear, the internet one.' She said 'Grandad, it's basically the same - you can't see it and you don't understand it!'",
        "My memory's not what it used to be. Also, my memory's not what it used to be.",
        "The advantage of being my age? I can hide my own Easter eggs!",
        "I'm at that age where my back goes out more than I do."
    ],
    
    "witty": [
        "At my age, 'getting lucky' means finding my car in the car park.",
        "I'm not saying I'm old, but my birth certificate is in Roman numerals.",
        "The good news about Alzheimer's? You meet new people every day! Even if they're the same people.",
        "Age is just a number. In my case, a rather large, complicated number.",
        "I've reached the age where 'happy hour' is a nap."
    ],
    
    "wordplay": [
        "Why don't we ever see elephants hiding in trees? Because they're so good at it!",
        "What do you call a bear with no teeth? A gummy bear!",
        "Why did the scarecrow win an award? He was outstanding in his field!",
        "What do you call a factory that makes good products? A satisfactory!",
        "Why did the bicycle fall over? It was two tired!"
    ],
    
    "british_humor": [
        "I went to the doctor. I said 'It hurts when I do this.' He said 'Well, don't do that then!'",
        "British weather forecast: Rain. Tomorrow: Also rain. Weekend: Don't get your hopes up.",
        "I asked for a cup of tea. They said 'How do you take it?' I said 'Very seriously.'",
        "What's the difference between a British wedding and a British funeral? One less drunk at the funeral.",
        "How do you know if someone's British? Don't worry, they'll apologize for something that wasn't their fault."
    ]
}


def get_story(theme: str = "classic", length: str = "medium") -> Dict[str, str]:
    """
    Get a story from the library
    
    Args:
        theme: Story theme (classic, nostalgia, wartime, bedtime, seaside, village, nature, gentle_humor)
        length: Story length (short, medium, long)
        
    Returns:
        Dictionary with title, content, delivery_notes
    """
    # Get stories matching theme
    matching_stories = STORIES.get(theme, STORIES["classic"])
    
    # Filter by length if possible, otherwise return any
    length_filtered = [s for s in matching_stories if s.get("length") == length]
    if not length_filtered:
        length_filtered = matching_stories
    
    # Pick random story
    story = random.choice(length_filtered)
    
    return {
        "title": story["title"],
        "content": story["content"].strip(),
        "delivery_notes": story["delivery_notes"],
        "theme": theme,
        "length": story.get("length", length)
    }


def get_joke(style: str = "gentle") -> str:
    """
    Get a joke from the collection
    
    Args:
        style: Joke style (gentle, witty, wordplay, british_humor)
        
    Returns:
        Joke string
    """
    jokes = JOKES.get(style, JOKES["gentle"])
    return random.choice(jokes)


def get_available_themes() -> List[str]:
    """Get list of available story themes"""
    return list(STORIES.keys())


def get_available_joke_styles() -> List[str]:
    """Get list of available joke styles"""
    return list(JOKES.keys())


# Story delivery instructions for Serenity AI
STORYTELLING_DELIVERY_GUIDE = """
When telling stories from the library:

1. VOICE MODULATION:
   - Use expressive, theatrical delivery
   - Vary pace: slower for atmosphere, faster for excitement
   - Include natural pauses for dramatic effect
   - Inject warmth and nostalgia into historical tales

2. EMOTIONAL RESONANCE:
   - Honor the era and experiences being described
   - For wartime stories: respect and admiration
   - For nostalgia: gentle longing and warmth
   - For bedtime: soothing, calm rhythm
   - For humor: light, amused tone

3. ENGAGEMENT:
   - Follow delivery_notes provided with each story
   - Use sound emphasis (ting-a-ling, rustled, echo)
   - Allow emotional moments to breathe
   - End with warmth and connection

4. BRITISH AUTHENTICITY:
   - Maintain British cultural references naturally
   - Use appropriate era-specific language
   - Honor the British stoicism and humor in wartime tales
   - Embrace understatement in humorous moments

5. PERSONALIZATION:
   - After story, invite user to share their own memories
   - "Does that remind you of anything from your own childhood?"
   - "Did you have a sweet shop in your neighborhood?"
   - Connect stories to user's life experiences
"""
