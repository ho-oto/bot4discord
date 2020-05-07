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
        rsa_private_key_data=os.environ['BOX_APPAUTH_PRIVATEKEY'].replace(
            '\\n', '\n').encode(),
        rsa_private_key_passphrase=os.environ['BOX_APPAUTH_PASSPHRASE'].encode(
        ),
    ))
folder = client_box.folder(os.environ['BOX_DIR_ID'])

savedir = Path('/tmp')
uploaddir = Path('/tmp/upload')
if not uploaddir.exists():
    uploaddir.mkdir()


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
        await message.channel.send(
            'name = {}, id = {}'.format(item.name, item.id),
            file=discord.File(item_save)
        )
    if message.content.startswith('!!!p'):
        for search_query in message.content.split(" ")[1:]:
            items = list(client_box.search().query(query=search_query))
            if len(items) == 0:
                continue
            item = items[0]
            item_save = str(savedir / item.name)
            with open(item_save, 'wb') as file:
                client_box.file(item.id).download_to(file)
            await message.channel.send(
                'name = {}, id = {}'.format(item.name, item.id),
                file=discord.File(item_save)
            )
    if message.content == '!!!upload':
        for attachment in message.attachments:
            if attachment.filename.endswith(('.jpg', '.jpeg', '.png', '.gif'))\
                    and attachment.size < 10485760:
                await attachment.save(str(uploaddir / attachment.filename))
                newfile = folder.upload(str(uploaddir / attachment.filename))
                if newfile.type == 'error':
                    await message.channel.send(
                        'failed to upload {}'.format(attachment.filename)
                    )
                else:
                    await message.channel.send(
                        '{} was uploaded. ID = {}'.format(
                            newfile.name, newfile.id
                        ))
    if message.content.startswith('!!!delete'):
        fileid = message.content.split(' ')[1]
        resp = client_box.file(file_id=fileid).delete()
        if resp is None:
            await message.channel.send(
                'file with ID = {} was deleted'.format(fileid)
            )
    if message.content == '!!!list':
        await message.channel.send('{}'.format(os.environ['BOX_URL']))
    if message.content == '!!!help':
        s = '{} に置いてある画像を表示するbot\n'\
            '使い方\n'\
            '    `!!!p` : Boxの中からランダムな画像を表示\n'\
            '    `!!!p name` : Boxの中をnameで検索してヒットしたものを表示'\
            'する。スペース区切りで複数指定すると順番に表示する。\n'\
            '    `!!!list` : 画像リストのURLを表示する\n'\
            '    `!!!upload` : 画像をアップロードする。jpg, jpeg, png, gifのみ\n'\
            '    `!!!delete file_id` : 画像をBOXから削除する。file_idはBOXで'\
            '画像を開いたときのURLの末尾の数字。ファイル名では指定できない。\n'\
            '    `!!!rename file_id new_name` : file_idの画像をnew_nameに'\
            'リネームする。ファイル名では指定できない。\n'\
            '    `!!!help` : これを表示する。'.format(os.environ['BOX_URL'])
        await message.channel.send(s)

client_discord.run(TOKEN)
