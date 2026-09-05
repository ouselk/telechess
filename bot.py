import chess
from dbhelper import DBHelper
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Updater, InlineQueryHandler, CallbackQueryHandler

TOKEN = ''

VIEW_BLACK_PAWN = '⚫️'
VIEW_WHITE_PAWN = '⚪️'
VIEW_BLACK_ROOK = '🗻'
VIEW_WHITE_ROOK = '🏔'
VIEW_BLACK_KNIGHT = '🐴'
VIEW_WHITE_KNIGHT = '🦄'
VIEW_BLACK_BISHOP = '👮🏿‍♀️'
VIEW_WHITE_BISHOP = '👮‍♀️'
VIEW_BLACK_QUEEN = '👳🏿'
VIEW_WHITE_QUEEN = '👳🏻'
VIEW_BLACK_KING = '🎩'
VIEW_WHITE_KING = '👑'

RESULT_WHITE_VICTORY = 0
RESULT_BLACK_VICTORY = 1
RESULT_DRAW = 2

white_player = None
black_player = None

CONTEXT = None

DBHELPER = DBHelper()

def view_board(board):
    fen = board.fen()
    hs = fen.split('/')
    hs[7] = hs[7][:hs[7].index(' ')]

    row = []
    keyboard = []

    #распарсиваем fen натацию,
    #приводя всё к виду доски из inline кнопок,
    #где текстом является внешнее отображение ячейки,
    #а кэлбэк датой - её координаты.
    x = 0
    y = 8
    for h in hs:
        x = 0
        for s in h:
            x += 1
            if s.isnumeric():
                for e in range(int(s)):
                    txt = ' ' if (x+y) % 2 else '.'
                    row.append(InlineKeyboardButton(text=txt, callback_data=str(x) + str(y)))
                    x += 1
                else:
                    x -= 1
            else:
                if (s == 'p'):
                    s = VIEW_BLACK_PAWN
                elif (s == 'P'):
                    s = VIEW_WHITE_PAWN
                elif (s == 'r'):
                    s = VIEW_BLACK_ROOK
                elif (s == 'R'):
                    s = VIEW_WHITE_ROOK
                elif (s == 'n'):
                    s = VIEW_BLACK_KNIGHT
                elif (s == 'N'):
                    s = VIEW_WHITE_KNIGHT
                elif (s == 'b'):
                    s = VIEW_BLACK_BISHOP
                elif (s == 'B'):
                    s = VIEW_WHITE_BISHOP
                elif (s == 'q'):
                    s = VIEW_BLACK_QUEEN
                elif (s == 'Q'):
                    s = VIEW_WHITE_QUEEN
                elif (s == 'k'):
                    s = VIEW_BLACK_KING
                elif (s == 'K'):
                    s = VIEW_WHITE_KING
                row.append(InlineKeyboardButton(text=s, callback_data=str(x) + str(y)))
        keyboard.append(row)
        row = []
       
        y -= 1

    row.append(InlineKeyboardButton(text='Ничья', callback_data='draw'))
    row.append(InlineKeyboardButton(text='Сдаться', callback_data='surrender'))
    keyboard.append(row)

    return InlineKeyboardMarkup(keyboard)


def view_text(query, context):
    text = '*Шахматы*\n\n'

    session_id = query.inline_message_id
    wp = context.bot_data[session_id]['white_player']
    bp = context.bot_data[session_id]['black_player']
    game_over = context.bot_data[session_id]['game_over']
    result = context.bot_data[session_id]['game_result']
    board = context.bot_data[session_id]['board']
    draw_offering = context.bot_data[session_id]['draw_offering']

    if (query.data == 'create_game'):
        text += wp.mention_markdown() + ' ожидает противника.'

    else:
        text += 'Играют: ' + wp.mention_markdown() + ' ' + VIEW_WHITE_KING +\
                ', ' + bp.mention_markdown() + ' ' + VIEW_BLACK_KING + '\n\n'

        if (game_over == False):
            text += 'Ходит: ' + ((wp.mention_markdown() + ' ' + VIEW_WHITE_KING)
                    if board.turn else (bp.mention_markdown() + ' ' + VIEW_BLACK_KING))

            if (draw_offering != None):
                text += '\n' + draw_offering.mention_markdown() + ' предлагает ничью.'

        elif (game_over == True):
            if (result == RESULT_DRAW):
                text += 'Ничья.'
            elif (result == RESULT_WHITE_VICTORY):
                text += 'Победитель: ' + wp.mention_markdown() + ' ' + VIEW_WHITE_KING
            elif (result == RESULT_BLACK_VICTORY):
                text += 'Победитель: ' + bp.mention_markdown() + ' ' + VIEW_BLACK_KING

    return text


def inline_query_handler(update, context):
    global CONTEXT
    CONTEXT = context

    markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text='Создать игру', callback_data="create_game")]])

    results = [InlineQueryResultArticle(
        1,
        'Шахматы',
        InputTextMessageContent('Шахматы\n\nЧтобы создать игру нажмите кнопку'),
        markup,
        description='' )]
    
    update.inline_query.answer(results)



def main_callback_query_handler(update, context):
    query = update.callback_query

    # Отсеиваем попытку взаимодействия с оконченными играми
    if (context.bot_data.get(query.inline_message_id) != None and
            context.bot_data[query.inline_message_id]['game_over']):
        DBHELPER.get_info(query.inline_message_id)
        return query.answer(text='Игра окончена', show_alert=True)

    # Отсеиваем попытку наблюдателя влезть в не своё дело
    if (context.bot_data.get(query.inline_message_id) != None and
            context.bot_data[query.inline_message_id].get('white_player') != None and
            context.bot_data[query.inline_message_id].get('black_player') != None and
            (query.from_user.id != context.bot_data[query.inline_message_id]['white_player'].id and
                query.from_user.id != context.bot_data[query.inline_message_id]['black_player'].id)):
            return query.answer(text='Вас не звали', show_alert=True)
    
    if (query.data == 'create_game' or query.data == 'join_to_game'):
        return register_handler(update, context)
    
    elif (query.data == 'draw'):
        return draw_handler(update, context)

    elif (query.data == 'surrender'):
        return surrender_handler(update, context)

    else:
        return game_handler(update, context)

def surrender_handler(update, context):
    query = update.callback_query

    session_id = query.inline_message_id
    white_player = context.bot_data[session_id]['white_player']
    board = context.bot_data[session_id]['board']

    result = RESULT_BLACK_VICTORY if query.from_user == white_player else RESULT_WHITE_VICTORY

    context.bot_data[session_id]['game_over'] = True
    context.bot_data[session_id]['game_result'] = result

    query.edit_message_text(text=view_text(query, context),
        reply_markup=view_board(board), parse_mode='markdown')
    query.answer()


def draw_handler(update, context):
    # Достаём плэеров, что бы узнать кто решил сдаться
    session_id = query.inline_message_id
    wp = context.bot_data[session_id]['white_player']
    bp = context.bot_data[session_id]['black_player']
    board = context.bot_data[session_id]['board']
    draw_offering = context.bot_data[session_id]['draw_offering']

    # Узнаём, была ли это жалкая просьба или снисходительное 'да'
    # и решаем вопрос подобающе
    if (draw_offering == None):
        context.bot_data[session_id]['draw_offering'] = query.from_user

        query.edit_message_text(text=view_text(query, context),
                reply_markup=view_board(board), parse_mode='markdown')
        query.answer()

    elif (draw_offering == query.from_user):
        query.answer(text='Жди ответа соперника', show_alert=True)

    elif (draw_offering != None and 
            draw_offering != query.from_user):
       context.bot_data[session_id]['game_over'] = True
       context.bot_data[session_id]['game_result'] = RESULT_DRAW
       query.edit_message_text(text=view_text(query, context), 
               reply_markup=view_board(board), parse_mode='markdown')
       query.answer()

def get_square(x, y):
    # По стандарным координатам тут вычисляем номер квадрата;

    letters = ' abcdefgh'
    if (type(x) == type('')
            and not x.isnumeric()):
            x = letters.index(x)

    x = int(x)
    y = int(y)

    square = ((8*y) + (x - 9))

    return square


def game_handler(update, context):

    query = update.callback_query

    # Обеспечиваем возможность
    # проводить много матчей одновременно.
    session_id = query.inline_message_id
    board = context.bot_data[session_id]['board']
    white_player = context.bot_data[session_id]['white_player']
    black_player = context.bot_data[session_id]['black_player']
    cell_selected = context.bot_data[session_id]['cell_selected']
    figure_selected = context.bot_data[session_id]['figure_selected']

    # Отсеиваем попытки пойти не на своем ходе
    current_player = white_player if board.turn else black_player
    if (current_player.id != query.from_user.id):
        query.answer(text='Дождись своего хода')
        return

    square = get_square(query.data[0], query.data[1])
    if board.piece_at(square) and\
            board.piece_at(square).color == board.turn:     # Если на выбранной ячейке фигура цвета игрока - выбрать её
        figure_selected = query.data
        print('figure_selected begin ' + figure_selected)
    elif (figure_selected):                                 # Если же нет, но при том фигура уже выбрана - выбрать ячейку
        cell_selected = query.data
        print('cell selected begin ' + cell_selected)
    else:                                                   # В остальных случаях, указать на то, что фигура не выбрана
        query.answer(text='Выбери фигуру, которой хочешь пойти')

    if figure_selected and cell_selected:
        letters = ' abcdefgh'
        uci = (letters[int(figure_selected[0])] + figure_selected[1] +
               letters[int(cell_selected[0])] + cell_selected[1])

        if (chess.Move.from_uci(uci) in board.legal_moves):
            board.push_uci(uci)
            context.bot_data[session_id]['draw_offering'] = None                  # Если был сделан ход, то предложение о ничье сбрасывается
            current_player = white_player if board.turn else black_player         # Почему то эта хуйня, объявленная раньше не работает, разобраться надо блять
            query.edit_message_text(text=view_text(query, context), 
                  reply_markup=view_board(board), parse_mode='markdown')
        else:
        #Замена пешек, дошедших до конца на ферзя
            for m in board.legal_moves:
                if (len(str(m))==5 and uci in str(m)):
                    board.push_uci(uci+'q')
                    current_player = white_player if board.turn else black_player # Тут по той же причине
                    query.edit_message_text(text=view_text(query, context), 
                          reply_markup=view_board(board), parse_mode='markdown')
                else:
                    query.answer(text='Так ходить нельзя', show_alert=False)
        figure_selected = None
        cell_selected = None

    if board.is_game_over():
        context.bot_data[session_id]['game_over'] = True
        if (board.result() == '1-0'):         # White power
            context.bot_data[session_id]['game_result'] = RESULT_WHITE_VICTORY
        elif (board.result() == '0-1'):       # Black win (fight but not war, sieg hail)
            context.bot_data[session_id]['game_result'] = RESULT_BLACK_VICTORY
        elif (board.result() == '1/2-1/2'):   # Draw
            context.bot_data[session_id]['game_result'] = RESULT_DRAW
        query.edit_message_text(text=view_text(query, context),
                reply_markup=view_board(board), parse_mode='markdown')

        DBHELPER.make_record(session_id)
        DBHELPER.get_info(session_id)


    query.answer()

    # Возвращаем, чё украли
    context.bot_data[session_id]['board'] = board
    context.bot_data[session_id]['white_player'] = white_player
    context.bot_data[session_id]['black_player'] = black_player
    context.bot_data[session_id]['cell_selected'] = cell_selected
    context.bot_data[session_id]['figure_selected'] = figure_selected


def register_handler(update, context):
    query = update.callback_query

    session_id = query.inline_message_id

    if (query.data == 'create_game'):

        white_player = query.from_user

        context.bot_data[session_id] = {}
        context.bot_data[session_id]['white_player'] = white_player
        context.bot_data[session_id]['black_player'] = None
        context.bot_data[session_id]['board'] = None
        context.bot_data[session_id]['cell_selected'] = None
        context.bot_data[session_id]['figure_selected'] = None
        context.bot_data[session_id]['draw_offering'] = None
        context.bot_data[session_id]['game_over'] = False
        context.bot_data[session_id]['game_result'] = None

        query.edit_message_text(text=view_text(query, context), parse_mode='markdown',
                reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(text='Присоедениться', callback_data='join_to_game')]]))

    elif (query.data == 'join_to_game'):
        white_player = context.bot_data[session_id]['white_player']

        if (white_player.id == query.from_user.id):
            query.answer(text='тише сиди', show_alert=True)
            return

        black_player = query.from_user
        board = chess.Board()

        context.bot_data[session_id]['black_player'] = black_player
        context.bot_data[session_id]['board'] = board

        query.edit_message_text(text=view_text(query, context), 
                reply_markup=view_board(board), parse_mode='markdown')

def main():
    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher

    dp.add_handler(InlineQueryHandler(inline_query_handler))
    dp.add_handler(CallbackQueryHandler(main_callback_query_handler))


    updater.start_polling()

main()
