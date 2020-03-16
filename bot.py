import discord
import asyncio
from pathlib import Path
from unicodedata import normalize
import re
from datetime import date
import os
from dotenv import load_dotenv
import redis

db = redis.StrictRedis(host='localhost', port=6379, db=1, charset="utf-8", decode_responses=True)
print("Redis connection:", db.ping())

GUILD_NAME = "course_label"

starting_time = date.today().isoformat()

def to_key(s):
    string = normalize("NFD", s.upper()).encode("ASCII", "ignore").decode("ASCII")
    string = re.sub(r"\W", " ", string)
    return frozenset(string.split())

students = dict()
for student in Path(f"{GUILD_NAME}.tsv").read_text().split("\n"):
    if student:
        key = to_key(student)
        value = student.replace("\t", " ")
        students[key] = value
    
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bg_task = self.loop.create_task(self.my_background_task())

    async def on_ready(self):
        self.guild = discord.utils.get(client.guilds, name=GUILD_NAME)
        if not self.guild:
            return print(f"No guild named '{GUILD_NAME}'.")
        print(f'{client.user} is connected to the following guild:')
        print(f'{self.guild.name} (id: {self.guild.id})')
        print(f'{client.user} has connected to Discord!')
        expected = set(students)
        for member in self.guild.members:
            nick = member.nick if member.nick else member.name
            if nick in ("prof_nickname", "Poll Bot", "Roll call", "TeXit"):
                continue
            key = to_key(nick)
            if key not in students:
                print(f"@{nick} : attention ! mets ton pseudo sous la forme « Prénom Nom » pour éviter d'être automatiquement noté(e) absent(e) par le robot d'appel.")
            else:
                expected.discard(key)
        for key in expected:
            print(f"Attention ! {students[key]} n'est pas trouvé(e) par le robot d'appel.")
        print("@everyone Pour les autres étudiants, pas de problème avec votre pseudo, il est bien reconnu par mon petit robot.")


    async def my_background_task(self):
        await self.wait_until_ready()
        await asyncio.sleep(2) # seconds
        while not self.is_closed():
            if not hasattr(self, "guild"):
                continue
            online_members = set()
            for member in self.guild.members:
                if str(member.status) in ('online', 'dnd'):
                    online_members.add(to_key(member.nick if member.nick else member.name))
            row = []
            for (i, (student_key, student_name)) in enumerate(students.items()):
                is_present = "." if student_key in online_members else "F"
                row.append(is_present)
                if is_present == "F":
                    print(f"{student_name}: absent")
                db.append(f"roll_call:{GUILD_NAME}:{starting_time}:{student_name}", is_present)
            print("".join(row))
            await asyncio.sleep(60) # seconds

client = MyClient()
client.run(TOKEN)
