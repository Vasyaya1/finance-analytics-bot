from aiogram.fsm.state import State, StatesGroup


class MicroTransactionState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_category = State()

class OptimizeBudgetState(StatesGroup):
    waiting_for_percent = State()

class NLPTrainingState(StatesGroup):
    waiting_for_category = State()
