# region python library imports
import discord
import asyncio
import datetime
import os
# endregion

# region .env file load
from dotenv import load_dotenv, dotenv_values
load_dotenv()
config = dotenv_values(".env")
print(config)
# endregion

# region Discord library set up
intents = discord.Intents.default()
intents.reactions = True
client = discord.Client(intents=intents)
# endregion

# region channel ID variables 
wfhchannel_id = int(os.getenv("USER_REQUEST_CHANNEL_ID"))
wfh_requestchannel_id = int(os.getenv("CONFIRM_REQUEST_CHANNEL_ID"))
confirmation_channel_id = int(os.getenv("CONFIRMATION_MESSAGE_CHANNEL_ID"))
decline_wfh_channel_id = int(os.getenv("DECLINE_MESSAGE_CHANNEL_ID"))
# endregion

# region reaction emoji store
weekday_reaction_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
# endregion

# region bot live indicator
@client.event
# function which will let the user know that the bot is now active
async def on_ready():
    print(f'Logged in as {client.user.name} - {client.user.id}')
    await schedule_message()
# endregion

# region fetch schedule message config values
def get_configuration_values():
    wfhchannel_id = int(os.getenv("USER_REQUEST_CHANNEL_ID"))
    weekday_int = int(os.getenv("WEEKDAY_INT")) - 1
    hour = int(os.getenv("HOUR"))
    minute = int(os.getenv("MINUTE"))
    reactions = weekday_reaction_emojis
    return wfhchannel_id, weekday_int, hour, minute, reactions
# endregion

# region calculate time until next event function
def calculate_next_event(wfhchannel_id, weekday_int, hour, minute, reactions):
    now = datetime.datetime.now()

    # set the time of the next scheduled event
    next_event = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # calculate the days until the next scheduled event on the specified weekday
    days_until_next_event = (weekday_int - next_event.weekday()) % 7
    next_event += datetime.timedelta(days=days_until_next_event)
    
    # if the next event time is in the past, move it to the same time next week
    if now >= next_event:
        next_event += datetime.timedelta(days=7)
    
    # calculate the time remaining until the next event in seconds
    time_until_next_event = (next_event - now).total_seconds()
    #print(time_until_next_event)
    
    # return the calculated values
    return next_event, days_until_next_event, time_until_next_event
# endregion


# region generate wfh home request message
async def send_wfh_message(channel, reactions):
    message_content = (
        "@everyone\nPlease book your work from home days:\n\n"
        f"Tuesday: {reactions[0]}\nWednesday: {reactions[1]}\nThursday: {reactions[2]}\nFriday: {reactions[3]}\n\n"
        "Please select a maximum of 2 days; exceeding this limit may result in your request being declined."
    )
    message = await channel.send(message_content)

    for reaction in reactions:
        await message.add_reaction(reaction)
# endregion

# region parent function for scheduling message request
async def schedule_message():
    try:
        # retrieve configuration values for scheduling
        wfhchannel_id, weekday_int, hour, minute, reactions = get_configuration_values()

        # loop to repeatedly check to schedule the message
        while True:
            # calculate details about the next event
            next_event, days_until_next_event, time_until_next_event = calculate_next_event(wfhchannel_id, weekday_int, hour, minute, reactions)
            now = datetime.datetime.now()

            # check if it's time to send the message
            if days_until_next_event == 0 and now.hour == hour and now.minute == minute:
                channel = client.get_channel(wfhchannel_id)
                await send_wfh_message(channel, reactions)

            # sleep until the next event time
            await asyncio.sleep(time_until_next_event)

    except Exception as e:
        # handle exceptions, if any, and print an error message
        print(f"An error occurred in the schedule_message function: {e}")
# endregion


# region WFH Confirmation/Decline Function
@client.event
async def on_reaction_add(reaction, user):
    try:
        # Ignore bot's own reactions
        if user == client.user:
            return

        # Check if the reaction is added in the WFH request channel
        if reaction.message.channel.id == wfhchannel_id:
            emoji = str(reaction.emoji)
            message_contents = generate_wfh_request_message(user.mention, emoji)
            if message_contents:
                # Send the request message to the confirmation channel and add reaction emojis
                target_channel = client.get_channel(wfh_requestchannel_id)
                target_message = await target_channel.send(message_contents)
                await target_message.add_reaction("✅")
                await target_message.add_reaction("❌")
        
        # Check if the reaction is added in the confirmation/decline channel
        elif reaction.message.channel.id == wfh_requestchannel_id:
            emoji = str(reaction.emoji)
            message_content_parts = reaction.message.content.split()
            selected_day = message_content_parts[8].rstrip('.')
            user_request = message_content_parts[0]
            
            if emoji in ["✅", "❌"]:
                # Determine the appropriate channel based on the reaction
                confirm_channel = client.get_channel(confirmation_channel_id if emoji == "✅" else decline_wfh_channel_id)
                declined_user = user.mention if emoji == "❌" else ""
                
                confirmation_message = (
                    "Please remember to add your WFH days to base camp." if emoji == "✅"
                    else f"Please speak with {declined_user} if you have any questions."
                )
                
                message = (
                    f"{user_request}, your work from home request for {selected_day} has been {'declined.' if emoji == '❌' else 'confirmed.'}\n"
                    f"{confirmation_message}"
                )
                await confirm_channel.send(message)
                
    except Exception as e: # In case of API error, execute this except statement
        print(f"An error occurred in the on_reaction_add function: {e}")
# endregion

# region WFH request message generator
def generate_wfh_request_message(requesting_user, emoji):
    day_map = {
        "1️⃣": "Tuesday",
        "2️⃣": "Wednesday",
        "3️⃣": "Thursday",
        "4️⃣": "Friday"
    }
    
    selected_day = day_map.get(emoji)
    if selected_day is not None:
        return f"{requesting_user} has requested to work from home on {selected_day}.\n✅ Confirm\n ❌ Decline"
    return None
# endregion

# Replace 'YOUR_TOKEN' with your actual bot token
client.run(os.getenv("BOT_TOKEN"))