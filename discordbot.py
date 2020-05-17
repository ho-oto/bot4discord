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
folder_music_upload = client_box.folder(os.environ['BOX_DIR_ID_MUSIC_UPLOAD'])

download_dir = Path('/tmp')
upload_dir = Path('/tmp/upload')
if not upload_dir.exists():
    upload_dir.mkdir()

music_suffics = ['mp3', 'm4a', 'wav', 'ac3']
picture_suffics = ['jpg', 'jpeg', 'JPG', 'JPEG', 'png', 'gif', 'bmp']


class Picture(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['r', ''], help="""（`!!r`,`!!`も可）ランダム表示
        引数で検索して結果の中からランダム表示
        引数無しの場合はBox全体の中からランダム表示
    """)
    async def random(self, ctx, *args):
        if len(args) == 0:
            await random_all(ctx)
        else:
            await _search(ctx, args, which='r')

    @commands.command(aliases=['s', 'p'], help="""（`!!s`,`!!p`も可）検索表示
        引数で検索して最上位の画像を表示
    """)
    async def search(self, ctx, *args):
        if len(args) == 0:
            await random_all(ctx)
        else:
            await _search(ctx, args, which='s')


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="""検索して音楽再生
    """)
    async def play(self, ctx, searchquery):
        if (not ctx.author.voice) or (not ctx.author.voice.channel):
            await ctx.send('please connect to voice channel')
            return

        items = list(client_box.search().query(
            query=searchquery,
            ancestor_folders=[folder_music, folder_music_upload],
            file_extensions=music_suffics
        ))

        if len(items) == 0:
            await ctx.send('no hitted results')
            return
        else:
            item = items[0]
            item_save = str(download_dir / item.name)
            await ctx.send('download {}'.format(item.name))
            with open(item_save, 'wb') as file:
                client_box.file(item.id).download_to(file)
            await ctx.send('download finish')

        await ctx.author.voice.channel.connect()
        ctx.message.guild.voice_client.play(discord.FFmpegPCMAudio(item_save))

    @commands.command(help="""再生終了
    """)
    async def stop(self, ctx):
        vc = ctx.message.guild.voice_client
        if vc is None:
            return
        await vc.disconnect()

    @commands.command(help="""一時停止
    """)
    async def pause(self, ctx):
        vc = ctx.message.guild.voice_client
        if vc is None:
            return
        vc.pause()

    @commands.command(help="""再開
    """)
    async def resume(self, ctx):
        vc = ctx.message.guild.voice_client
        if vc is None:
            return
        vc.resume()


async def random_all(ctx):
    items = list(folder_picture.get_items())
    if len(items) == 0:
        return
    item = choice(items)
    item_save = str(download_dir / item.name)
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
            file_extensions=picture_suffics
        ))
        if len(items) == 0:
            continue
        if which == 'r':
            item = choice(items)
        elif which == 's':
            item = items[0]
        item_save = str(download_dir / item.name)
        with open(item_save, 'wb') as file:
            client_box.file(item.id).download_to(file)
        await ctx.send(
            '**name = {}** (id = {})'.format(item.name, item.id),
            file=discord.File(item_save)
        )


class File(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help='BoxのURLを表示')
    async def url(self, ctx):
        await ctx.send('view:   {}\nupload: {}'.format(
            os.environ['BOX_URL'], os.environ['BOX_URL_UPLOAD_PICTURE']
        ))

    @commands.command(help='Boxにアップロード（jpg, jpeg, png, gif）')
    async def upload(self, ctx):
        for attachment in ctx.message.attachments:
            if attachment.filename.endswith(tuple(picture_suffics)) and\
                    attachment.size < 10485760:

                await attachment.save(str(upload_dir / attachment.filename))
                newfile = folder_picture.upload(
                    str(upload_dir / attachment.filename)
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

    @commands.command(help="""Boxからファイルを削除
        file_id（ファイル名ではない）を指定する
        file_idはファイルをブラウザのBoxで開いたときのURLの末尾の数字
    """)
    async def delete(self, ctx, *args):
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

    @commands.command(help="""Box内のファイルのリネーム
        file_id（ファイル名ではない）とnew_nameを指定する（例：!!rename 123456 hoge.png）
        file_idは画像をブラウザのBoxで開いたときのURLの末尾の数字
    """)
    async def rename(self, ctx, fileid, newname):
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


bot = commands.Bot(command_prefix=['!!'], case_insensitive=True)

bot.add_cog(Picture(bot))
bot.add_cog(Music(bot))
bot.add_cog(File(bot))

bot.run(os.environ['DISCORD_TOKEN'])
