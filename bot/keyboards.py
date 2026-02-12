"""
Keyboard layouts for Telegram bot.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from typing import List, Tuple


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Get main menu keyboard.

    Returns:
        ReplyKeyboardMarkup object
    """
    keyboard = [
        [KeyboardButton("Поиск задач"), KeyboardButton("Подборка по сложности")],
        [KeyboardButton("Поиск по тегам"), KeyboardButton("Статистика")],
        [KeyboardButton("Настройки"), KeyboardButton("Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_rating_keyboard() -> InlineKeyboardMarkup:
    """
    Get keyboard for rating selection.

    Returns:
        InlineKeyboardMarkup object
    """
    keyboard = [
        [
            InlineKeyboardButton("800-1200", callback_data="rating_800_1200"),
            InlineKeyboardButton("1300-1600", callback_data="rating_1300_1600")
        ],
        [
            InlineKeyboardButton("1700-2000", callback_data="rating_1700_2000"),
            InlineKeyboardButton("2100-2400", callback_data="rating_2100_2400")
        ],
        [
            InlineKeyboardButton("2500-2800", callback_data="rating_2500_2800"),
            InlineKeyboardButton("2900-3500", callback_data="rating_2900_3500")
        ],
        [InlineKeyboardButton("Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_tag_keyboard(tags: List[str], page: int = 0, items_per_page: int = 8) -> Tuple[InlineKeyboardMarkup, int]:
    """
    Get paginated keyboard for tag selection.

    Args:
        tags: List of all tags
        page: Current page number
        items_per_page: Number of tags per page

    Returns:
        Tuple of (InlineKeyboardMarkup, total_pages)
    """
    total_pages = (len(tags) + items_per_page - 1) // items_per_page
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    current_tags = tags[start_idx:end_idx]

    keyboard = []

    # Add tag buttons
    for tag in current_tags:
        keyboard.append([
            InlineKeyboardButton(tag, callback_data=f"tag_{tag}")
        ])

    # Add navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("<", callback_data=f"tag_page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(">", callback_data=f"tag_page_{page + 1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Add action buttons
    keyboard.append([InlineKeyboardButton("Готово", callback_data="tags_done")])
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_main")])

    return InlineKeyboardMarkup(keyboard), total_pages


def get_selected_tags_keyboard(selected_tags: List[str], all_tags: List[str]) -> InlineKeyboardMarkup:
    """
    Get keyboard showing selected tags.

    Args:
        selected_tags: List of already selected tags
        all_tags: List of all available tags

    Returns:
        InlineKeyboardMarkup object
    """
    keyboard = []

    # Show selected tags
    if selected_tags:
        for i in range(0, len(selected_tags), 2):
            row = []
            for j in range(2):
                if i + j < len(selected_tags):
                    tag = selected_tags[i + j]
                    row.append(InlineKeyboardButton(
                        f"✓ {tag}",
                        callback_data=f"remove_tag_{tag}"
                    ))
            keyboard.append(row)

    # Add action buttons
    keyboard.append([
        InlineKeyboardButton("Найти задачи", callback_data="find_by_tags")
    ])
    keyboard.append([
        InlineKeyboardButton("Добавить теги", callback_data="add_more_tags")
    ])
    if selected_tags:
        keyboard.append([
            InlineKeyboardButton("Очистить все", callback_data="clear_tags")
        ])
    keyboard.append([
        InlineKeyboardButton("Назад", callback_data="back_to_main")
    ])

    return InlineKeyboardMarkup(keyboard)


def get_task_action_keyboard(task_id: int, contest_id: int, index: str) -> InlineKeyboardMarkup:
    """
    Get keyboard for task actions.

    Args:
        task_id: Database task ID
        contest_id: Codeforces contest ID
        index: Problem index

    Returns:
        InlineKeyboardMarkup object
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "Открыть на Codeforces",
                url=f"https://codeforces.com/problemset/problem/{contest_id}/{index}"
            )
        ],
        [
            InlineKeyboardButton("Назад", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_simple_keyboard() -> InlineKeyboardMarkup:
    """
    Get simple inline keyboard with back button.

    Returns:
        InlineKeyboardMarkup object
    """
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """
    Get confirmation keyboard (Yes/No).

    Returns:
        InlineKeyboardMarkup object
    """
    keyboard = [
        [
            InlineKeyboardButton("Да", callback_data="confirm_yes"),
            InlineKeyboardButton("Нет", callback_data="confirm_no")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
