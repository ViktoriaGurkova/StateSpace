from collections import defaultdict

import numpy as np

from functions import *

from scipy.linalg import expm


class StateSpace:
    def __init__(self, M, a, b, capacity1, capacity2, lambda1, lambda2, mu):
        self.M = M
        self.a = a
        self.b = b
        self.lambda1 = lambda1
        self.lambda2 = lambda2
        self.mu = mu
        self.queue_capacity = [capacity1, capacity2]

        self.x = M // a
        print('Максимальное число требований 1го класса = ', self.x)
        self.y = M // b
        print('Максимальное число требований 2го класса = ', self.y)

    def start(self):
        server_states = self.get_server_states()
        print("Состояния фрагментов на системах (не включая очереди):")
        for state_id, state in enumerate(server_states):
            print('S' + str(state_id), '= ', pretty_server_state(state))

        states = self.get_all_state_with_queues(server_states)
        print("\nСостояния системы вместе с очередями:")

        for state_id, state in enumerate(states):
            print('S' + str(state_id), '= ', pretty_state(state))

        Q = self.create_generator(states)

        print('Q = ', Q)
        # нужно будет проверить кооректность заполнения матрицы,
        # удобно скопировать в excel
        # и применить условное форматирование
        np.savetxt("Q.txt", Q, fmt='%0.0f')

        distr = expm(Q * 1000000000)[0]
        print('Стационарное распределение P_i:', distr)
        for i, p_i in enumerate(distr):
            print('P[', pretty_state(states[i]), '] =', p_i)
        print(sum(distr))

    def get_server_states(self):
        server_states = set()
        for i in range(self.x + 1):
            for j in range(self.y + 1):
                total_number_of_tasks = self.a * i + self.b * j
                if self.M < total_number_of_tasks:
                    continue
                X = sorted(get_lots_of_fragments(i, self.a))
                Y = sorted(get_lots_of_fragments(j, self.b))
                server_states.update(itertools.product(X, Y))
        return server_states

    def get_all_state_with_queues(self, server_states: set):
        states = []
        queue_states = set(itertools.product(range(self.queue_capacity[0] + 1), range(self.queue_capacity[1] + 1)))

        for q_state in queue_states:
            for server_state in server_states:
                if self.is_possible_state(q_state, server_state):
                    states.append((q_state, server_state))
        return states

    def is_possible_state(self, q_state, state):
        number_of_free_servers = self.number_of_free_servers_for_server_state(state)
        if q_state[0] and number_of_free_servers >= self.a:
            return False
        if q_state[1] and number_of_free_servers >= self.b:
            return False
        return True

    # возвращает словарь {состояние: интенсивность перехода}
    def get_achievable_states(self, current_state: tuple):
        states_and_rates = defaultdict(float)

        print('#' * 100)
        print('Рассмотрим состояние ' + pretty_state(current_state))

        capacity1 = self.queue_capacity[0]
        capacity2 = self.queue_capacity[1]

        # получаем различные характеристики состояния
        q1 = current_state[0][0]
        print('q1 = ', q1)
        q2 = current_state[0][1]
        print('q2 = ', q2)
        server_state = current_state[1]
        print('server_state = ', server_state)

        number_of_free_servers = self.number_of_free_servers_for_server_state(server_state)
        print("Число свободных приборов", number_of_free_servers)

        print("ПОСТУПЛЕНИЕ")
        if q1 != capacity1:
            if number_of_free_servers < self.a:
                new_state = create_state(q1 + 1, q2, server_state[0], server_state[1])
                print(f'Поступление требования первого класса в очередь с интенсивностью {self.lambda1} и переход в стояние ',
                      pretty_state(new_state))
                states_and_rates[new_state] += self.lambda1
            else:
                updated_first_demands_tasks = server_state[0]
                updated_first_demands_tasks += (self.a,)
                new_state = create_state(q1, q2, updated_first_demands_tasks, server_state[1])
                print(f'Поступление требования первого класса с интенсивностью {self.lambda1} и немедленное начало его '
                      'обслуживания и переход в состояние ', pretty_state(new_state))
                states_and_rates[new_state] += self.lambda1
        else:
            print("Очередь заполнена - требование потерялось")

        if q2 != capacity2:
            if number_of_free_servers < self.b:
                new_state = create_state(q1, q2 + 1, server_state[0], server_state[1])
                print(f'Поступление требования второго класса в очередь с интенсивностью {self.lambda2} и переход в стояние ',
                      pretty_state(new_state))
                states_and_rates[new_state] += self.lambda2
            else:
                updated_second_demands_tasks = server_state[1]
                updated_second_demands_tasks += (self.b,)
                new_state = create_state(q1, q2, server_state[0], updated_second_demands_tasks)
                print(f'Поступление требования второго класса с интенсивностью {self.lambda2} и немедленное начало его '
                      ' обслуживания и переход в состояние ', pretty_state(new_state))
                states_and_rates[new_state] += self.lambda2
        else:
            print("Очередь заполнена - требование потерялось")

        print('УХОД')
        # 1й класс
        for state_id, number_of_lost_tasks_in_demand in enumerate(server_state[0]):
            updated_first_demands_tasks = list(server_state[0])
            updated_second_demands_tasks = list(server_state[1])
            copy_q1 = q1
            copy_q2 = q2
            copy_number_of_free_servers = number_of_free_servers
            if number_of_lost_tasks_in_demand == 1:
                updated_first_demands_tasks.pop(state_id)
                if q1:
                    updated_first_demands_tasks += [self.a]
                    copy_q1 = q1 - 1
                elif q2:
                    while copy_number_of_free_servers + self.a >= self.b and copy_q2:
                        updated_second_demands_tasks += [self.b]
                        copy_q2 -= 1
                        copy_number_of_free_servers -= self.b
                new_state = create_state(copy_q1, copy_q2, updated_first_demands_tasks, updated_second_demands_tasks)
                print(f'Завершение обслуживания всего требования первого класса с интенсивностью {self.mu}',
                      'и переход в состояние ', pretty_state(new_state))
                states_and_rates[new_state] += self.mu

            else:
                leave_intensity = self.mu * updated_first_demands_tasks[state_id]
                updated_first_demands_tasks[state_id] -= 1
                new_state = create_state(q1, q2, updated_first_demands_tasks, server_state[1])
                print(f'Завершение обслуживания фрагмента требования первого класса с интенсивностью {leave_intensity}',
                      'и переход в состояние ', pretty_state(new_state))
                states_and_rates[new_state] += leave_intensity

        # 2й класс
        for state_id, number_of_lost_tasks_in_demand in enumerate(server_state[1]):
            updated_first_demands_tasks = list(server_state[0])
            updated_second_demands_tasks = list(server_state[1])
            copy_q1 = q1
            copy_q2 = q2
            copy_number_of_free_servers = number_of_free_servers
            if number_of_lost_tasks_in_demand == 1:
                updated_second_demands_tasks.pop(state_id)
                if q2:
                    updated_second_demands_tasks += [self.b]
                    copy_q2 = q2 - 1
                elif q1:
                    while copy_number_of_free_servers + self.b >= self.a and copy_q1:
                        updated_first_demands_tasks += [self.a]
                        copy_q1 -= 1
                        copy_number_of_free_servers -= self.a
                new_state = create_state(copy_q1, copy_q2, updated_first_demands_tasks, updated_second_demands_tasks)
                print(f'Завершение обслуживания всего требования второго класса с интенсивностью {self.mu}',
                      'и переход в состояние ', pretty_state(new_state))
                states_and_rates[new_state] += self.mu

            else:
                leave_intensity = self.mu * updated_second_demands_tasks[state_id]
                updated_second_demands_tasks[state_id] -= 1
                new_state = create_state(q1, q2, server_state[0], updated_second_demands_tasks)
                print(f'Завершение обслуживания фрагмента требования второго класса с интенсивностью {leave_intensity}',
                      'и переход в состояние ', pretty_state(new_state))
                states_and_rates[new_state] += leave_intensity

        return states_and_rates

    def create_generator(self, states: list):
        n = len(states)
        Q = np.zeros((n, n))
        # проходим по каждому состоянию и смотрим на его смежные
        for i, current_state in enumerate(states):
            states_and_rates = self.get_achievable_states(current_state)
            for state, rate in states_and_rates.items():
                # текущее состояние имеет номер i, смотрим на номер j смежного состояния
                j = states.index(state)
                # снова делаем += а не просто равно, чтобы не перетереть результаты перехода
                Q[i, j] += rate

        for i, row in enumerate(Q):
            Q[i, i] = -sum(row)

        return Q

    def number_of_free_servers_for_server_state(self, server_state):
        number = self.M - (len(server_state[0]) * self.a + len(server_state[1]) * self.b)
        if number < 0:
            raise Exception("Number of free servers for states < 0, it is not correct state")
        return number


if __name__ == '__main__':
    _M = 5
    _a = 3
    _b = 2
    _capacity1 = 5
    _capacity2 = 5
    _lambda1 = 1
    _lambda2 = 2
    _mu = 3

    sp = StateSpace(_M, _a, _b, _capacity1, _capacity2, _lambda1, _lambda2, _mu)

    sp.start()