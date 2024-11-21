import discord
from discord.ext import commands
from discord.ext.commands import Context
import speech_recognition as sr
import asyncio

class LanguageSelectionView(discord.ui.View):
    def __init__(self, message: discord.Message):
        super().__init__()
        self.message = message  # Store the message to delete later
        self.selected_language = None  # Initialize selected_language to None

    @discord.ui.button(label="English", style=discord.ButtonStyle.primary)
    async def english_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.selected_language = "en"  # Store the selected language
        await self.message.delete()  # Delete the embed message
        self.stop()  # Stop the view

    @discord.ui.button(label="Vietnamese", style=discord.ButtonStyle.primary)
    async def vietnamese_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.selected_language = "vi"  # Store the selected language
        await self.message.delete()  # Delete the embed message
        self.stop()  # Stop the view

class Voice(commands.Cog, name="voice"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.listen_task = None  # Store the task for listening to voice

    @commands.hybrid_command(
        name="join",
        description="Join your voice channel and start speech-to-text.",
    )
    async def join(self, context: Context) -> None:
        if context.author.voice:
            channel = context.author.voice.channel
            await channel.connect()
            await context.send(f"Joined {channel.name}!")

            # Ask for language selection
            embed = discord.Embed(
                title="Language Selection",
                description="Please select a language for speech recognition:",
                color=discord.Color.blue()
            )

            # Send the embed message and store it
            message = await context.send(embed=embed)
            view = LanguageSelectionView(message)
            await message.edit(view=view)  # Edit the original message to include the view

            # Wait for the user to select a language
            await view.wait()

            if view.selected_language:
                language = view.selected_language
                await context.send(f"Selected language: {language}")

                # Start listening to the voice channel in the background
                self.listen_task = self.bot.loop.create_task(self.listen_to_voice(context, language))
            else:
                await context.send("No language selected. Command cancelled.")
        else:
            await context.send("You need to be in a voice channel to use this command.")

    async def listen_to_voice(self, context: Context, language: str):
        voice_client = context.voice_client
        recognizer = sr.Recognizer()

        while voice_client.is_connected():
            try:
                # Here you would receive audio data from the voice channel and process it
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source)
                    audio = recognizer.listen(source)

                    # Recognize speech using Google Speech Recognition
                    try:
                        text = recognizer.recognize_google(audio, language=language)
                        await context.send(text)  # Send recognized text to the channel
                    except sr.UnknownValueError:
                        pass  # Do nothing if speech is not recognized
                    except sr.RequestError as e:
                        await context.send(f"Could not request results from Google Speech Recognition service; {e}")

            except Exception as e:
                await context.send(f"An error occurred: {e}")
                break

            await asyncio.sleep(0.2)  # Small delay to prevent overloading the API

    @commands.hybrid_command(
        name="leave",
        description="Leave the voice channel and cancel all operations.",
    )
    async def leave(self, context: Context) -> None:
        if context.voice_client:
            if self.listen_task and not self.listen_task.done():
                self.listen_task.cancel()  # Cancel the listening task if it's running
                await context.send("Speech-to-text operation canceled.")
            await context.voice_client.disconnect()  # Disconnect the bot from the voice channel
            await context.send("Disconnected from the voice channel!")
        else:
            await context.send("I am not connected to a voice channel.")

async def setup(bot) -> None:
    await bot.add_cog(Voice(bot))
