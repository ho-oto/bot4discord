from random import choice
from pathlib import Path
import os

import discord
from discord.ext import commands
import boxsdk

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
folder_picture = client_box.folder(os.environ['BOX_DIR_ID_PICTURE'])
folder_music = client_box.folder(os.environ['BOX_DIR_ID_MUSIC'])

savedir = Path('/tmp')
uploaddir = Path('/tmp/upload')
tmpmusicdir = Path('/tmp/music')
if not uploaddir.exists():
    uploaddir.mkdir()
if not tmpmusicdir.exists():
    tmpmusicdir.mkdir()

bot = commands.Bot(command_prefix=['!!!', '!!'], case_insensitive=True)


@bot.command(aliases=['r', ''], help="""（rのみでも可）ランダム表示
    検索ワードを付けた場合は検索結果の中からランダム表示
    コマンド単体の場合はBox全体の中からランダム表示
""")
async def random(ctx, *args):
    if len(args) == 0:
        await random_all(ctx)
    else:
        await _search(ctx, args, which='r')


@bot.command(aliases=['s', 'p'], help="""（sまたはpのみでも可）検索表示
    与えられた引数で検索して最上位の画像を表示
""")
async def search(ctx, *args):
    if len(args) == 0:
        await random_all(ctx)
    else:
        await _search(ctx, args, which='s')


async def random_all(ctx):
    items = list(folder_picture.get_items())
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
        items = list(client_box.search().query(
            query=search_query,
            ancestor_folders=[folder_picture],
            file_extensions=['jpg', 'jpeg', 'png', 'gif']
        ))
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


@bot.command(help='BoxのURLを表示')
async def url(ctx):
    await ctx.send('{}'.format(os.environ['BOX_URL']))


@bot.command(help='Boxにアップロード（jpg, jpeg, png, gif, mp3, m4a, wmv）')
async def upload(ctx):
    for attachment in ctx.message.attachments:
        if attachment.filename.endswith(
            ('.jpg', '.jpeg', '.png', '.gif', '.JPG', '.JPEG', '.PNG', '.GIF')
        ) and attachment.size < 10485760:

            await attachment.save(str(uploaddir / attachment.filename))
            newfile = folder_picture.upload(
                str(uploaddir / attachment.filename)
            )
            if newfile.type == 'error':
                await ctx.send(
                    'failed to upload {}'.format(attachment.filename)
                )
            else:
                await ctx.send(
                    '{} was uploaded (file_id = {})'.format(
                        newfile.name, newfile.id
                    ))

        elif attachment.filename.endswith(('.mp3', '.wmv', '.m4a')):

            await attachment.save(str(uploaddir / attachment.filename))
            newfile = folder_music.upload(
                str(uploaddir / attachment.filename)
            )
            if newfile.type == 'error':
                await ctx.send(
                    'failed to upload {}'.format(attachment.filename)
                )
            else:
                await ctx.send(
                    '{} was uploaded (file_id = {})'.format(
                        newfile.name, newfile.id
                    ))


@bot.command(help="""Boxからファイルを削除
    file_id（ファイル名ではない）を指定する
    file_idはファイルをブラウザのBoxで開いたときのURLの末尾の数字
""")
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


@bot.command(help="""Box内のファイルのリネーム
    file_id（ファイル名ではない）とnew_nameを指定する（例：!!rename 123456 hoge.png）
    file_idは画像をブラウザのBoxで開いたときのURLの末尾の数字
""")
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


@bot.command(help="""音楽再生
""")
async def music(ctx, searchquery):
    if (not ctx.author.voice) or (not ctx.author.voice.channel):
        await ctx.send('please connect to voice channel')
        return

    items = list(client_box.search().query(
        query=searchquery,
        ancestor_folders=[folder_music],
        file_extensions=['mp3', 'wmv', 'm4a']
    ))

    if len(items) == 0:
        await ctx.send('no hitted results')
        return
    else:
        item = items[0]
        item_save = str(tmpmusicdir / item.name)
        await ctx.send('download {}'.format(item.name))
        with open(item_save, 'wb') as file:
            client_box.file(item.id).download_to(file)
        await ctx.send('download finish')

    await ctx.author.voice.channel.connect()
    ctx.message.guild.voice_client.play(discord.FFmpegPCMAudio(item_save))


@bot.command(help="""再生終了
""")
async def stop(ctx):
    if ctx.message.guild.voice_client is not None:
        await ctx.message.guild.voice_client.disconnect()


@bot.command(aliases=['resume'], help="""一時停止/再開
""")
async def pause(ctx):
    vc = ctx.message.guild.voice_client
    if vc is None:
        return
    if vc.is_paused():
        vc.resume()
    if vc.is_playng():
        vc.pause()


bot.run(os.environ['DISCORD_TOKEN'])
