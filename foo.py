#!/usr/bin/env python3
import argparse
import asyncio

from typing import Tuple
import treys

from tg.bot import Bot
import tg.types as pokerTypes

parser = argparse.ArgumentParser(
    prog='Template bot',
    description='A Turing Games poker bot that always checks or calls, no matter what the target bet is (it never folds and it never raises)')

parser.add_argument('--port', type=int, default=1999,
                    help='The port to connect to the server on')
parser.add_argument('--host', type=str, default='localhost',
                    help='The host to connect to the server on')
parser.add_argument('--room', type=str, default='my-new-room',
                    help='The room to connect to')
parser.add_argument('--simulations', type=int, default=3000)

parser.add_argument('--username', type=str, default='bot',
                    help='The username for this bot (make sure it\'s unique)')

args = parser.parse_args()

cnt = 0

array = [
    [7, -351, -334, -314, -318, -308, -264, -217, -166, -113, -53, 10, 98],
    [-279, 74, -296, -274, -277, -267, -251, -201, -148, -93, -35, 27, 116],
    [-263, -225, 142, -236, -240, -231, -209, -185, -130, -75, -17, 46, 134],
    [-244, -206, -169, 207, -201, -189, -169, -148, -114, -55, 2, 68, 153],
    [-247, -208, -171, -138, 264, -153, -134, -108, -78, -43, 19, 85, 154],
    [-236, -200, -162, -125, -91, 324, -99, -72, -43, -6, 37, 104, 176],
    [-192, -182, -143, -108, -75, -43, 384, -39, -4, 29, 72, 120, 197],
    [-152, -134, -122, -84, -50, -17, 16, 440, 28, 65, 106, 155, 215],
    [-104, -86, -69, -56, -19, 12, 47, 81, 499, 102, 146, 195, 254],
    [-52, -35, -19, 0, 11, 46, 79, 113, 149, 549, 161, 212, 271],
    [2, 21, 34, 55, 72, 86, 121, 153, 188, 204, 598, 228, 289],
    [63, 79, 98, 116, 132, 151, 168, 200, 235, 249, 268, 647, 305],
    [146, 164, 180, 198, 198, 220, 240, 257, 291, 305, 323, 339, 704]
]

prob_arr = []
opp_most_recent = {'type': None, 'amount': None}


def transform_array(arr):
    return [[(x/1000 + 1) / 3 for x in row] for row in arr]


def card_name(card: pokerTypes.Card):
    val = str(card.rank)
    if card.rank == 1:
        val = 'A'
    if card.rank == 10:
        val = 'T'
    elif card.rank == 11:
        val = 'J'
    elif card.rank == 12:
        val = 'Q'
    elif card.rank == 13:
        val = 'K'
    return f"{val}{card.suit[0]}"


class TemplateBot(Bot):
    def act(self, state, hand):
        me = None
        self.my_id = 'bread'
        for player in state.players:
            if player.id == self.my_id:
                me = player
                break

        opp = None
        for player in state.players:
            if player.id != self.my_id:
                opp = player
                break

        print("pot is", state.pot, "i have", me.stack)

        cost_to_play = min(state.target_bet - me.current_bet, me.stack)

        board = [treys.Card.new(card_name(card)) for card in state.cards]

        if len(board) == 0:
            score, prob = utility_score(self, state, hand)
            p = prob
            if score > 0:
                raise_to = min(score / 2, me.stack * 0.75)
            else:
                raise_to = score

        else:
            p = self.win_prob(state, hand)
            b = len(state.players)
            raise_to = (p - (1 - p) / b) * (me.stack) * 0.75

        print('my stack:', me.stack, raise_to, p, ''.join(map(card_name, hand)), ''.join(map(card_name, state.cards)))

        if opp.stack == 0:
            return {'type': 'call'}
        elif me.stack == 0:
            print('raise 800')
            return {'type': 'raise', 'amount': 15}

        elif raise_to > state.target_bet:
            print('raise ', raise_to - state.target_bet)
            return {'type': 'raise', 'amount': raise_to - state.target_bet}

        elif opp_most_recent['type'] == 'raise':
            potodds = opp_most_recent['amount'] / (state.pot + opp_most_recent['amount'] + cost_to_play)
            if p >= potodds:
                print('call')
                return {'type': 'call'}

        elif raise_to >= cost_to_play or cost_to_play <= 15:
            print('call')
            return {'type': 'call'}
        print('fold')
        return {'type': 'fold'}

    def opponent_action(self, action, player):
        global opp_most_recent
        print('opponent action?', action, player)
        opp_most_recent['type'] = action.type
        if action.type == 'raise':
            opp_most_recent['amount'] = action.amount
        """opp_most_recent['type'] = action['type']
        if action['type'] == 'raise':
            opp_most_recent['amount'] = action['amount']"""

    def game_over(self, payouts):
        global cnt
        print('game over', payouts)
        cnt += 1
        # print(cnt)

    def start_game(self, my_id):
        global prob_arr
        self.my_id = my_id
        prob_arr = transform_array(array)
        pass

    def win_prob(self, state: pokerTypes.PokerSharedState, hand: Tuple[pokerTypes.Card, pokerTypes.Card]):
        out = 0
        hand = [
            treys.Card.new(card_name(hand[0])),
            treys.Card.new(card_name(hand[1]))]
        board = [treys.Card.new(card_name(card)) for card in state.cards]

        evaluator = treys.Evaluator()
        for i in range(args.simulations):
            deck = treys.Deck()
            deck.shuffle()
            for card in hand + board:
                deck.cards.remove(card)
            pred = board + deck.draw(5 - len(board))
            score = evaluator.evaluate(hand, pred)
            other = 10 ** 9

            for player in state.players:
                if player.id != self.my_id:
                    other = min(other, evaluator.evaluate(deck.draw(2), pred))
            if score < other:
                out += 1
        return out / args.simulations


def utility_score(self, state: pokerTypes.PokerSharedState, hand: Tuple[pokerTypes.Card, pokerTypes.Card]):
    idx1 = hand[0].rank - 2
    if idx1 < 0:
        idx1 = 12
    idx2 = hand[1].rank - 2
    if idx2 < 0:
        idx2 = 12
    score = array[idx1][idx2]
    prob = prob_arr[idx1][idx2]
    return score, prob


if __name__ == "__main__":
    bot = TemplateBot(args.host, args.port, args.room, args.username)
    asyncio.run(bot.start())
