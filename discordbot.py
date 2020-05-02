from random import choice
from pathlib import Path
import os

import discord
import boxsdk

TOKEN = os.environ['DISCORD_TOKEN']
client_discord = discord.Client()

client_box = boxsdk.Client(
    boxsdk.JWTAuth(
        client_id=os.environ['BOX_CLIENT_ID'],
        client_secret=os.environ['BOX_CLIENT_SECLET'],
        enterprise_id=os.environ['BOX_ENTERPRISE_ID'],
        jwt_key_id=os.environ['BOX_APPAUTH_PUBLICKEYID'],
        rsa_private_key_data=os.environ['BOX_APPAUTH_PRIVATEKEY'].replace('\\n','\n').encode(),
        rsa_private_key_passphrase=os.environ['BOX_APPAUTH_PASSPHRASE'].encode(),
    ))
folder = client_box.folder(os.environ['BOX_DIR_ID'])

alias = {}
savedir = Path('/tmp')

@client_discord.event
async def on_message(message):
    if message.author.bot:
        return
    if message.content == '!!!p':
        items = list(folder.get_items())
        if len(items) == 0:
            return
        item = choice(items)
        item_save = str(savedir / item.name)
        with open(item_save, 'wb') as file:
            client_box.file(item.id).download_to(file)
        await message.channel.send(item.name, file=discord.File(item_save))
    if message.content.startswith('!!!p'):
        for search_query in message.content.split(" ")[1:]:
            items = list(client_box.search().query(query=search_query))
            if len(items) == 0:
                continue
            item = items[0]
            item_save = str(savedir / item.name)
            with open(item_save, 'wb') as file:
                client_box.file(item.id).download_to(file)
            await message.channel.send(item.name, file=discord.File(item_save))
    if message.content.startswith('!!!aa'):
        if len(message.content.split(" ")) == 3:
            k = str(message.content.split(" ")[1])
            v = str(message.content.split(" ")[2])
            alias[k] = v
            await message.channel.send('Alias added: {} => {}'.format(k, v))
    if message.content.startswith('!!!pa'):
        for keys in message.content.split(" ")[1:]:
            try:
                search_query = alias[str(keys)]
                items = list(client_box.search().query(query=search_query))
                if len(items) == 0:
                    continue
                item = items[0]
                item_save = str(savedir / item.name)
                with open(item_save, 'wb') as file:
                    client_box.file(item.id).download_to(file)
                await message.channel.send(item.name, file=discord.File(item_save))
            except BaseException:
                continue
    if message.content == '!!!la':
        s = 'list of aliases:\n'
        for k, v in alias.items():
            s += '{} => {}\n'.format(k, v)
        await message.channel.send(s)
    if message.content == '!!!help':
        s = '{} に'\
            '置いてある画像を表示するbot。真面目に作ってないのでBox内に画像以外'\
            'があるとそれをアップロードしちゃうので注意。\n'\
            '使い方\n'\
            '    `!!!p` : Boxの中からランダムな画像を表示\n'\
            '    `!!!p name` : Boxの中をnameで検索してヒットしたものを表示'\
            'する。スペース区切りで複数指定すると順番に表示する。\n'\
            '    `!!!aa key val` : エイリアスを足す。`!!!p val`のかわりに`!!!pa key`'\
            'が使えるようになる。永続化してないのでなんかあると消えると思うので、'\
            '多分Boxの中のファイル名を弄ったほうがはやい。\n'\
            '    `!!!pa name` : エイリアスを使って表示。\n'\
            '    `!!!la` : 登録されてるエイリアスを一覧表示する。\n'\
            '    `!!!help` : これを表示する。'.format(os.environ['BOX_URL'])
        await message.channel.send(s)

client_discord.run(TOKEN)
