import os
import re
import aiohttp
import discord
import google.generativeai as genai
from discord.ext import commands
from dotenv import load_dotenv
from discord.ext.commands import Context

load_dotenv()

# Google AI Key
GEMINI_API_KEY = os.getenv("GOOGLE_AI_KEY")
system_prompt = "You are a helpful bot!"

# AI Configuration
genai.configure(api_key=GEMINI_API_KEY)

# Define the generation configuration
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

# Create the model and start a chat session
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)
chat_session = model.start_chat(history=[])

# Define Cog for the bot
class Template(commands.Cog, name="ask"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="reset",
        description="This command will reset the conversation history with the bot."
    )
    async def reset(self, context: Context) -> None:
        # Clear the chat session history
        chat_session.history = []
        await context.send("🤖 Chat history has been reset.")

    @commands.hybrid_command(
        name="ask",
        description="This command will ask Gemini what you have asked me, with optional image support.",
    )
    async def ask(self, context: Context, *, query: str = "") -> None:
        async with context.typing():
            cleaned_text = clean_discord_message(query)

            if context.message.attachments:
                for attachment in context.message.attachments:
                    if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                        async with aiohttp.ClientSession() as session:
                            async with session.get(attachment.url) as resp:
                                if resp.status != 200:
                                    await context.send('Unable to download the image.')
                                    return
                                image_data = await resp.read()

                        # Append user's query with image information to history
                        chat_session.history.append({"role": "user", "parts": [cleaned_text]})
                        response_text = await generate_response_with_image_and_text(image_data, cleaned_text)

                        chat_session.history.append({"role": "model", "parts": [response_text]})
                        await split_and_send_messages(context, response_text, 1700)
                        return
            else:
                chat_session.history.append({"role": "user", "parts": [cleaned_text]})
                response_text = await generate_response_with_text(cleaned_text)
                chat_session.history.append({"role": "model", "parts": [response_text]})
                await split_and_send_messages(context, response_text, 1700)

    @commands.hybrid_command(
        name="history",
        description="This command will show your message history.",
    )
    async def history(self, context: Context) -> None:
        if not chat_session.history:
            await context.send("No conversation history available.")
            return

        history_output = ""
        for entry in chat_session.history:
            if isinstance(entry, dict) and "role" in entry and "parts" in entry:
                role = entry["role"].capitalize()
                content = ''.join(entry["parts"]).strip()
                highlighted_role = f"**{role}:**"
                history_output += f"{highlighted_role} {content}\n"

        await split_and_send_messages(context, history_output.strip(), 2000)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user or message.mention_everyone:
            return

        if self.bot.user in message.mentions or isinstance(message.channel, discord.DMChannel):
            cleaned_text = clean_discord_message(message.content)

            async with message.channel.typing():
                chat_session.history.append({"role": "user", "parts": [cleaned_text]})

                if message.attachments:
                    for attachment in message.attachments:
                        if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                            await message.add_reaction('🎨')
                            async with aiohttp.ClientSession() as session:
                                async with session.get(attachment.url) as resp:
                                    if resp.status != 200:
                                        await message.channel.send('Unable to download the image.')
                                        return
                                    image_data = await resp.read()
                                    response_text = await generate_response_with_image_and_text(image_data, cleaned_text)

                                    chat_session.history.append({"role": "model", "parts": [response_text]})
                                    await split_and_send_messages(message, response_text, 1700)
                                    return
                else:
                    await message.add_reaction('💬')
                    response_text = await generate_response_with_text(cleaned_text)

                    chat_session.history.append({"role": "model", "parts": [response_text]})
                    await split_and_send_messages(message, response_text, 1700)

# Helper functions for AI responses and splitting messages
async def generate_response_with_text(message_text):
    print("Got textPrompt: " + message_text)
    response = chat_session.send_message(message_text)
    
    if response._error:
        return "❌" + str(response._error)

    return response.text

async def generate_response_with_image_and_text(image_data, text):
    print("Got imagePrompt: " + text)
    image_parts = [{"mime_type": "image/jpeg", "data": image_data}]
    prompt_parts = [image_parts[0], f"\n{text if text else 'What is this a picture of?'}"]
    
    response = model.generate_content(prompt_parts)
    
    if response._error:
        print(f"Error in response: {response._error}")
        return "❌" + str(response._error)
    
    print(f"Response Text: {response.text}")
    return response.text

# Function to split and send long messages
async def split_and_send_messages(message_system, text, max_length):
    messages = [text[i:i + max_length] for i in range(0, len(text), max_length)]
    for msg in messages:
        await message_system.channel.send(msg)

# Cleaning Discord messages by removing text inside brackets
def clean_discord_message(input_string):
    return re.sub(r'<[^>]+>', '', input_string)

# Finally, we add the cog to the bot
async def setup(bot) -> None:
    await bot.add_cog(Template(bot))
