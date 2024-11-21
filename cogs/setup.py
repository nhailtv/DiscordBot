import discord
from discord.ext import commands
from discord.ext.commands import Context, has_permissions
import asyncio

class Setup(commands.Cog, name="setup"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.copied_channels = None

    @commands.command(
        name="copy",
        description="Copies the current server's channels and categories.",
    )
    @commands.is_owner()  # Only the server owner can execute this command
    async def copy(self, context: Context) -> None:
        """
        Copies the channels and categories from the server.

        :param context: The command context.
        """
        guild = context.guild
        self.copied_channels = []

        # Embed to display copied channels and categories
        embed = discord.Embed(
            title="Copied Channels and Categories",
            description=f"List of categories and channels copied from {guild.name}",
            color=discord.Color.blue()
        )

        for category in guild.categories:
            category_info = {
                'name': category.name,
                'channels': [{'name': channel.name, 'type': type(channel)} for channel in category.channels]
            }
            self.copied_channels.append(category_info)

            # Add category and channels to the embed
            channel_list = '\n'.join([f"- {channel['name']} ({'Text' if channel['type'] == discord.TextChannel else 'Voice'})" for channel in category_info['channels']])
            embed.add_field(name=f"Category: {category.name}", value=channel_list or "No channels", inline=False)

        await context.send(embed=embed)

    @commands.command(
    name="paste",
    description="Pastes the copied channels and categories into the server after confirmation.",
)
    @commands.is_owner()  # Only the server owner can execute this command
    async def paste(self, context: Context) -> None:
        """
        Pastes the copied channels and categories into the server, deleting existing ones after confirmation.

        :param context: The command context.
        """
        if not self.copied_channels:
            await context.send("No channels have been copied yet. Use the `copy` command first.")
            return

        def check(m):
            return m.author == context.author and m.channel == context.channel

        # Ask for confirmation twice before proceeding
        await context.send("Are you sure you want to delete all existing channels and paste the copied ones? (yes/no)")
        try:
            confirmation1 = await self.bot.wait_for("message", check=check, timeout=30.0)
            if confirmation1.content.lower() != "yes":
                await context.send("Paste operation canceled.")
                return

            await context.send("Are you really sure? This will delete all channels and paste the copied ones. (yes/no)")
            confirmation2 = await self.bot.wait_for("message", check=check, timeout=30.0)
            if confirmation2.content.lower() != "yes":
                await context.send("Paste operation canceled.")
                return
        except asyncio.TimeoutError:
            await context.send("Confirmation timed out. Paste operation canceled.")
            return

        # Delete all existing channels and categories sequentially
        for channel in context.guild.channels:
            await channel.delete()

        # Create channels and categories sequentially to ensure the correct order
        for category_info in self.copied_channels:
            await self.create_category_and_channels(context.guild, category_info)

    async def create_category_and_channels(self, guild: discord.Guild, category_info: dict) -> None:
        """
        Creates a category and its associated channels sequentially to ensure the correct order.

        :param guild: The guild to create the category in.
        :param category_info: A dictionary containing category name and channel information.
        """
        # Check if a category with the same name already exists
        existing_category = discord.utils.get(guild.categories, name=category_info['name'])
        if not existing_category:
            category = await guild.create_category(category_info['name'])
        else:
            category = existing_category

        # Create channels within the category sequentially to ensure the correct order
        for channel_info in category_info['channels']:
            if channel_info['type'] == discord.TextChannel:
                existing_channel = discord.utils.get(category.text_channels, name=channel_info['name'])
                if not existing_channel:
                    await category.create_text_channel(channel_info['name'])
            elif channel_info['type'] == discord.VoiceChannel:
                existing_channel = discord.utils.get(category.voice_channels, name=channel_info['name'])
                if not existing_channel:
                    await category.create_voice_channel(channel_info['name'])


# Adding the cog to the bot
async def setup(bot) -> None:
    await bot.add_cog(Setup(bot))
