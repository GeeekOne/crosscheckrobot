from aiogram import types, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Post
from aiogram.filters import Text

posts_router = Router()

# Состояния для работы с постами
class PostCreation(StatesGroup):
    waiting_for_content = State()
    waiting_for_title = State()

# Клавиатура "Посты"
posts_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Подготовить пост", callback_data="prepare_post")],
    [InlineKeyboardButton(text="Отправить пост", callback_data="send_post")]
])

# Подготовка поста
@posts_router.callback_query(lambda c: c.data == "prepare_post")
async def prepare_post(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Отправьте текст/картинку/видео для поста.")
    await state.set_state(PostCreation.waiting_for_content)

@posts_router.message(PostCreation.waiting_for_content)
async def receive_content(message: types.Message, state: FSMContext):
    media_type = None
    media_id = None

    # Проверяем содержимое сообщения
    if message.photo:
        media_type = "photo"
        media_id = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        media_id = message.video.file_id
    elif message.text:
        media_type = "text"

    # Сохраняем содержимое в FSM
    await state.update_data(media_type=media_type, media_id=media_id, content=message.text)
    await message.answer("Как назвать этот пост?")
    await state.set_state(PostCreation.waiting_for_title)

@posts_router.message(PostCreation.waiting_for_title)
async def receive_title(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    title = message.text

    # Сохраняем пост в базе
    new_post = Post(
        title=title,
        content=data.get("content"),
        media_type=data.get("media_type"),
        media_id=data.get("media_id")
    )
    session.add(new_post)
    await session.commit()

    await message.answer("Пост сохранен.", reply_markup=posts_menu)
    await state.clear()

# Отправка постов
@posts_router.callback_query(lambda c: c.data == "send_post")
async def choose_post(callback: types.CallbackQuery, session: AsyncSession):
    # Получаем список постов
    posts = await session.execute(Post.__table__.select())
    posts = posts.fetchall()

    # Формируем кнопки
    buttons = [
        [InlineKeyboardButton(text=post.title, callback_data=f"send_post_{post.id}")]
        for post in posts
    ]
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="back")])

    await callback.message.edit_text("Выберите пост:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@posts_router.callback_query(lambda c: c.data.startswith("send_post_"))
async def send_post(callback: types.CallbackQuery, session: AsyncSession):
    post_id = int(callback.data.split("_")[-1])
    post = await session.get(Post, post_id)

    # Отправляем пост в группу
    if post.media_type == "photo":
        await callback.bot.send_photo(chat_id=-1001234567890, photo=post.media_id, caption=post.content)
    elif post.media_type == "video":
        await callback.bot.send_video(chat_id=-1001234567890, video=post.media_id, caption=post.content)
    elif post.media_type == "text":
        await callback.bot.send_message(chat_id=-1001234567890, text=post.content)

    await callback.answer("Пост отправлен.")
