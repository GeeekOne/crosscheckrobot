from dataclasses import dataclass
from environs import Env


@dataclass
class TgBot:
    token: str
    group_id: int

@dataclass
class Config:
    tg_bot: TgBot


def load_config(path: str | None = None) -> Config:

    env: Env = Env()
    env.read_env(path)

    return Config(
        tg_bot=TgBot(
            token=env('TOKEN'),
            group_id=int(env('GROUP_ID'))
        )
    )