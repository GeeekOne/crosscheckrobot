from aiogram.fsm.state import State, StatesGroup

class SetCaptchaTimeStates(StatesGroup):
    waiting_for_captcha_time = State()