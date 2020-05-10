from random import choice
from pathlib import Path
import os

import discord
from discord.ext import commands
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


bot = commands.Bot(command_prefix='!!', case_insensitive=True)


@bot.command(aliases=['r', ''])
async def random(ctx, *args):
    if len(args) == 0:
        await random_all(ctx)
    else:
        await _search(ctx, args, which='r')


@bot.command(aliases=['s'])
async def search(ctx, *args):
    if len(args) == 0:
        await random_all(ctx)
    else:
        await _search(ctx, args, which='s')


async def random_all(ctx):
    items = list(folder.get_items())
    if len(items) == 0:
        return
    item = choice(items)
    item_save = str(savedir / item.name)
    with open(item_save, 'wb') as file:
        client_box.file(item.id).download_to(file)
    await ctx.send(
        '**name = {}** (id = {})'.format(item.name, item.id),
        file=discord.File(item_save)
    )


async def _search(ctx, args, which):
    for search_query in args:
        items = list(client_box.search().query(query=search_query))
        if len(items) == 0:
            continue
        if which == 'r':
            item = choice(items)
        elif which == 's':
            item = items[0]
        item_save = str(savedir / item.name)
        with open(item_save, 'wb') as file:
            client_box.file(item.id).download_to(file)
        await ctx.send(
            '**name = {}** (id = {})'.format(item.name, item.id),
            file=discord.File(item_save)
        )


@bot.command(name=['list'])
async def _list(ctx):
    await ctx.send('{}'.format(os.environ['BOX_URL']))


@bot.command()
async def upload(ctx):
    for attachment in ctx.message.attachments:
        if not attachment.filename.endswith(('.jpg', '.jpeg', '.png', '.gif'))\
                or attachment.size >= 10485760:
            continue

        await attachment.save(str(uploaddir / attachment.filename))
        newfile = folder.upload(str(uploaddir / attachment.filename))
        if newfile.type == 'error':
            await ctx.send(
                'failed to upload {}'.format(attachment.filename)
            )
        else:
            await ctx.send(
                '{} was uploaded (file_id = {})'.format(
                    newfile.name, newfile.id
                ))


@bot.command()
async def delete(ctx, *args):
    for fileid in args:
        response = client_box.file(file_id=fileid).delete()
        if response is not None:
            await ctx.send(
                'file with file_id = {} was deleted.'.format(fileid)
            )
        else:
            s = 'failed to remove file with file_id = {}. **NOTE: '\
                'file_id is not file name.**'.format(fileid)
            await ctx.send(s)


@bot.command()
async def rename(ctx, fileid, newname):
    oldfile = client_box.file(file_id=fileid).get()
    if oldfile is not None and oldfile.type != 'error':
        oldfile = oldfile.name
        if newname.split('.')[-1] != oldfile.split('.')[-1]:
            await ctx.send(
                'cannot change filename extension'
            )
        else:
            newfile = client_box.file(file_id=fileid).update_info(
                {'name': newname}
            )
            if newfile.type != 'error':
                await ctx.send(
                    'file {} (id : {}) -> {}'.format(
                        oldfile, fileid, newname
                    )
                )
            else:
                s = 'failed to rename '\
                    '(probably, {} already exists)'.format(newname)
                await ctx.send(s)
    else:
        s = 'cannot find file with id = {}. NOTE: '\
            'file_id is not file name. check !!!help'.format(fileid)
        await ctx.send(s)


client_discord.run(TOKEN)
