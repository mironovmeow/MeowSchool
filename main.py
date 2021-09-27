from bot import bot, auth_users_from_db


if __name__ == '__main__':
    bot.loop.run_until_complete(auth_users_from_db())
    bot.run_forever()
