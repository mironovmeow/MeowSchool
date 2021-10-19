from bot import auth_in_private_message, bot

if __name__ == '__main__':
    bot.loop.run_until_complete(auth_in_private_message())
    bot.run_forever()
