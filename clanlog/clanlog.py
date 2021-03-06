import discord
import os
from discord.ext import commands
from cogs.utils import checks
from .utils.dataIO import dataIO, fileIO
from __main__ import send_cmd_help
from copy import deepcopy
from time import time as get_time

import matplotlib.pyplot as plt
import matplotlib.dates as mdate
import matplotlib.ticker as ticker

import numpy as np
import clashroyale
import brawlstats

plt.switch_backend('agg')


class Clanlog:
    """Clan Log cog for LeGeND family"""

    def __init__(self, bot):
        self.bot = bot
        self.auth = self.bot.get_cog('crtools').auth
        self.clans = self.bot.get_cog('crtools').clans
        self.clubs = self.bot.get_cog('crtools').clubs
        self.tags = self.bot.get_cog('crtools').tags
        self.clash = clashroyale.OfficialAPI(self.auth.getOfficialToken(), is_async=True)
        self.brawl = brawlstats.Client(self.auth.getBSToken(), is_async=False)
        self.member_log = dataIO.load_json('data/clanlog/member_log.json')
        self.bs_member_log = dataIO.load_json('data/clanlog/bs_member_log.json')
        self.discord_log = dataIO.load_json('data/clanlog/discord_log.json')
        self.last_count = 0
        self.bs_last_count = 0

    def save_member_log(self):
        dataIO.save_json('data/clanlog/member_log.json', self.member_log)

    def save_bs_member_log(self):
        dataIO.save_json('data/clanlog/bs_member_log.json', self.bs_member_log)

    def update_member_log(self):
        self.member_log = dataIO.load_json('data/clanlog/member_log.json')

    def update_bs_member_log(self):
        self.member_log = dataIO.load_json('data/clanlog/bs_member_log.json')

    def update_discord_log(self):
        self.discord_log = dataIO.load_json('data/clanlog/discord_log.json')

    @checks.mod_or_permissions(administrator=True)
    @commands.command(pass_context=True, no_pm=True)
    async def clanlog(self, ctx, download=None):
        """Notifies whenever someone leaves or joins.
        Run this command on a schedule, do [p]clanlog download on first use."""

        old_clans = deepcopy(await self.clans.getClans())
        new_clans = deepcopy(old_clans)

        count = 0
        for clankey in self.clans.keysClans():
            try:
                clan = await self.clash.get_clan(await self.clans.getClanData(clankey, 'tag'))
            except clashroyale.RequestError:
                print("CLANLOG: Cannot reach Clash Royale Servers.")
                return

            count += clan.get("members")
            one_clan = {}
            for member in clan.member_list:
                tag = member.tag.strip("#")
                one_clan[tag] = {}
                one_clan[tag]["tag"] = tag
                one_clan[tag]["name"] = member.name
                one_clan[tag]["WarDayWins"] = 0
                one_clan[tag]["cardsEarned"] = 0
                if download is not None:
                    await self.clans.addMember(clankey, member.name, tag)
            new_clans[clankey]['members'] = one_clan

        if download is not None:
            return

        if self.last_count != count:
            self.update_member_log()
            current_time = get_time()
            self.member_log[str(current_time)] = count
            self.last_count = count

            saved_times = list(self.member_log.keys())
            for time in saved_times:
                if (current_time - float(time)) > 2678400:  # one month
                    self.member_log.pop(time, None)
            self.save_member_log()

        server = ctx.message.server

        for clankey in old_clans.keys():
            for member in old_clans[clankey]["members"].keys():
                if member not in new_clans[clankey]["members"]:
                    memberName = old_clans[clankey]["members"][member]["name"]
                    memberTag = old_clans[clankey]["members"][member]["tag"]
                    await self.clans.delMember(clankey, memberTag)

                    title = "{} (#{})".format(memberName, memberTag)
                    desc = "left **{}**".format(old_clans[clankey]["name"])
                    embed_left = discord.Embed(title=title,
                                               url="https://royaleapi.com/player/{}".format(memberTag),
                                               description=desc,
                                               color=0xff0000)

                    if server.id == "374596069989810176":
                        channel = await self.clans.getClanData(clankey, 'log_channel')
                        if channel is not None:
                            try:
                                await self.bot.send_message(discord.Object(id=channel), embed=embed_left)
                            except discord.errors.NotFound:
                                await self.bot.say("<#{}> NOT FOUND".format(channel))
                            except discord.errors.Forbidden:
                                await self.bot.say("No Permission to send messages in <#{}>".format(channel))

                    await self.bot.say(embed=embed_left)

        for clankey in self.clans.keysClans():
            for member in new_clans[clankey]["members"].keys():
                if member not in old_clans[clankey]["members"]:
                    memberName = new_clans[clankey]["members"][member]["name"]
                    memberTag = new_clans[clankey]["members"][member]["tag"]
                    await self.clans.addMember(clankey, memberName, memberTag)

                    title = "{} (#{})".format(memberName, memberTag)
                    desc = "joined **{}**".format(old_clans[clankey]["name"])

                    embed_join = discord.Embed(title=title,
                                               url="https://royaleapi.com/player/{}".format(memberTag),
                                               description=desc,
                                               color=0x00ff40)

                    if server.id == "374596069989810176":
                        channel = await self.clans.getClanData(clankey, 'log_channel')
                        if channel is not None:
                            try:
                                await self.bot.send_message(discord.Object(id=channel), embed=embed_join)
                            except discord.errors.NotFound:
                                await self.bot.say("<#{}> NOT FOUND".format(channel))
                            except discord.errors.Forbidden:
                                await self.bot.say("No Permission to send messages in <#{}>".format(channel))

                    await self.bot.say(embed=embed_join)

    @checks.mod_or_permissions(administrator=True)
    @commands.command(pass_context=True, no_pm=True)
    async def clublog(self, ctx, download=None):
        """Notifies whenever someone leaves or joins.
        Run this command on a schedule, do [p]clublog download on first use."""

        old_clubs = deepcopy(await self.clubs.getClubs())
        new_clubs = deepcopy(old_clubs)

        count = 0
        for clubkey in self.clubs.keysClubs():
            try:
                club = self.brawl.get_club(await self.clubs.getClubData(clubkey, 'tag'))
            except brawlstats.RequestError:
                print("CLANLOG: Cannot reach Brawl Stars Servers.")
                return

            count += club.members_count
            one_club = {}
            for member in club.members:
                tag = member.tag
                one_club[tag] = {}
                one_club[tag]["tag"] = tag
                one_club[tag]["name"] = member.name
                if download is not None:
                    await self.clubs.addMember(clubkey, member.name, tag)
            new_clubs[clubkey]['members'] = one_club

        if download is not None:
            return

        if self.bs_last_count != count:
            self.update_bs_member_log()
            current_time = get_time()
            self.bs_member_log[str(current_time)] = count
            self.bs_last_count = count

            saved_times = list(self.bs_member_log.keys())
            for time in saved_times:
                if (current_time - float(time)) > 2678400:  # one month
                    self.bs_member_log.pop(time, None)
            self.save_bs_member_log()

        server = ctx.message.server

        for clubkey in old_clubs.keys():
            for member in old_clubs[clubkey]["members"].keys():
                if member not in new_clubs[clubkey]["members"]:
                    memberName = old_clubs[clubkey]["members"][member]["name"]
                    memberTag = old_clubs[clubkey]["members"][member]["tag"]
                    await self.clubs.delMember(clubkey, memberTag)

                    title = "{} (#{})".format(await self.tags.formatName(memberName), memberTag)
                    desc = "left **{}**".format(old_clubs[clubkey]["name"])
                    embed_left = discord.Embed(title=title,
                                               url="https://brawlstats.com/profile/{}".format(memberTag),
                                               description=desc,
                                               color=0xff0000)

                    if server.id == "515502772926414933":
                        channel = await self.clubs.getClubData(clubkey, 'log_channel')
                        if channel is not None:
                            try:
                                await self.bot.send_message(discord.Object(id=channel), embed=embed_left)
                            except discord.errors.NotFound:
                                await self.bot.say("<#{}> NOT FOUND".format(channel))
                            except discord.errors.Forbidden:
                                await self.bot.say("No Permission to send messages in <#{}>".format(channel))

                    await self.bot.say(embed=embed_left)

        for clubkey in self.clubs.keysClubs():
            for member in new_clubs[clubkey]["members"].keys():
                if member not in old_clubs[clubkey]["members"]:
                    memberName = new_clubs[clubkey]["members"][member]["name"]
                    memberTag = new_clubs[clubkey]["members"][member]["tag"]
                    await self.clubs.addMember(clubkey, memberName, memberTag)

                    title = "{} (#{})".format(await self.tags.formatName(memberName), memberTag)
                    desc = "joined **{}**".format(old_clubs[clubkey]["name"])

                    embed_join = discord.Embed(title=title,
                                               url="https://brawlstats.com/profile/{}".format(memberTag),
                                               description=desc,
                                               color=0x00ff40)

                    if server.id == "515502772926414933":
                        channel = await self.clubs.getClubData(clubkey, 'log_channel')
                        if channel is not None:
                            try:
                                await self.bot.send_message(discord.Object(id=channel), embed=embed_join)
                            except discord.errors.NotFound:
                                await self.bot.say("<#{}> NOT FOUND".format(channel))
                            except discord.errors.Forbidden:
                                await self.bot.say("No Permission to send messages in <#{}>".format(channel))

                    await self.bot.say(embed=embed_join)

    @commands.group(pass_context=True, no_pm=True)
    async def history(self, ctx):
        """Graph with member count history"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @history.command(pass_context=True, no_pm=True, name="clash")
    async def history_clash(self, ctx):
        """Graph with clash member count history"""
        try:
            channel = ctx.message.channel
            await self.bot.send_typing(channel)
            self.update_member_log()

            secs, vals = zip(*sorted(self.member_log.items()))

            # Convert to the correct format for matplotlib.
            # mdate.epoch2num converts epoch timestamps to the right format for matplotlib
            secs = mdate.epoch2num(np.array(secs, dtype=float))

            fig, ax = plt.subplots(figsize=(10, 6))

            # Plot the date using plot_date rather than plot
            ax.plot_date(secs, vals, linestyle='solid', marker='None')

            # Choose your xtick format string
            date_fmt = '%a, %b %d %Y'
            tick_spacing = 3

            # Use a DateFormatter to set the data to the correct format.
            date_formatter = mdate.DateFormatter(date_fmt)
            ax.xaxis.set_major_formatter(date_formatter)
            ax.xaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))

            plt.title("CR MEMBER HISTORY OF LEGEND FAMILY", color="orange", weight="bold", size=19)
            plt.xlabel("DATE", color="gray")
            plt.ylabel("MEMBERS", color="gray")

            # Sets the tick labels diagonal so they fit easier.
            fig.autofmt_xdate()

            plt.savefig("data/clanlog/history.png")
            await self.bot.send_file(channel, "data/clanlog/history.png", filename=None)

        except (IndexError):
            await self.bot.say("Clanlog command needs to collect more data!")

    @history.command(pass_context=True, no_pm=True, name="brawl")
    async def history_brawl(self, ctx):
        """Graph with brawl member count history"""
        try:
            channel = ctx.message.channel
            await self.bot.send_typing(channel)
            self.update_member_log()

            secs, vals = zip(*sorted(self.bs_member_log.items()))

            # Convert to the correct format for matplotlib.
            # mdate.epoch2num converts epoch timestamps to the right format for matplotlib
            secs = mdate.epoch2num(np.array(secs, dtype=float))

            fig, ax = plt.subplots(figsize=(10, 6))

            # Plot the date using plot_date rather than plot
            ax.plot_date(secs, vals, linestyle='solid', marker='None')

            # Choose your xtick format string
            date_fmt = '%a, %b %d %Y'
            tick_spacing = 3

            # Use a DateFormatter to set the data to the correct format.
            date_formatter = mdate.DateFormatter(date_fmt)
            ax.xaxis.set_major_formatter(date_formatter)
            ax.xaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))

            plt.title("BS MEMBER HISTORY OF LEGEND FAMILY", color="orange", weight="bold", size=19)
            plt.xlabel("DATE", color="gray")
            plt.ylabel("MEMBERS", color="gray")

            # Sets the tick labels diagonal so they fit easier.
            fig.autofmt_xdate()

            plt.savefig("data/clanlog/history.png")
            await self.bot.send_file(channel, "data/clanlog/history.png", filename=None)

        except (IndexError):
            await self.bot.say("Clanlog command needs to collect more data!")

    @history.command(pass_context=True, no_pm=True, name="discord")
    async def history_discord(self, ctx):
        """Graph with discord user count history"""
        try:
            channel = ctx.message.channel
            server = ctx.message.server
            await self.bot.send_typing(channel)
            self.update_discord_log()

            secs, vals = zip(*sorted(self.discord_log[server.id].items()))

            # Convert to the correct format for matplotlib.
            # mdate.epoch2num converts epoch timestamps to the right format for matplotlib
            secs = mdate.epoch2num(np.array(secs, dtype=float))

            fig, ax = plt.subplots(figsize=(10, 6))

            # Plot the date using plot_date rather than plot
            ax.plot_date(secs, vals, linestyle='solid', marker='None')

            # Choose your xtick format string
            date_fmt = '%a, %b %d %Y'
            tick_spacing = 3

            # Use a DateFormatter to set the data to the correct format.
            date_formatter = mdate.DateFormatter(date_fmt)
            ax.xaxis.set_major_formatter(date_formatter)
            ax.xaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))

            plt.title("DISCORD USER HISTORY OF {}".format(server.name.upper()), color="#7289DA", weight="bold", size=19)
            plt.xlabel("DATE", color="gray")
            plt.ylabel("MEMBERS", color="gray")

            # Sets the tick labels diagonal so they fit easier.
            fig.autofmt_xdate()

            plt.savefig("data/clanlog/history.png")
            await self.bot.send_file(channel, "data/clanlog/history.png", filename=None)

        except (IndexError):
            await self.bot.say("Clanlog command needs to collect more data!")


def check_files():
    f = "data/clanlog/member_log.json"
    if not fileIO(f, "check"):
        print("Creating empty member_log.json...")
        fileIO(f, "save", {"1524540132": 0})
    f = "data/clanlog/bs_member_log.json"
    if not fileIO(f, "check"):
        print("Creating empty bs_member_log.json...")
        fileIO(f, "save", {"1524540132": 0})
    f = "data/clanlog/discord_log.json"
    if not fileIO(f, "check"):
        print("Creating empty discord_log.json...")
        fileIO(f, "save", {"1524540132": 0})


def check_folders():
    if not os.path.exists("data/clanlog"):
        print("Creating data/clanlog folder...")
        os.makedirs("data/clanlog")


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Clanlog(bot))
