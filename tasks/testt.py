#! coding: utf-8

# Тестовое приложение для проекта Opal
# Вычисление значений синуса по формулам Тейлора
# Вычисляет значения для указанного диапазона с заданной точностью
#   и нужным количеством шагов

import sys
import json
import time

def write(msg):
    sys.stdout.write(str(msg) + '\n')
    sys.stdout.flush()

def sin_taylor(x, n):
    f  = 1
    s  = 0.0
    e  = 1.0
    x0 = x
    for i in xrange(n + 1):
        #print e, f, x
        f *= (2 * i) * (2 * i + 1) if i else 1
        s += e * x / f
        x *= x0 * x0
        e *= -1
    return s

def answer(p, c = ''):
    return json.dumps({
        "answer": "ok",
        "value": p,
        "comment": c
    })

def error(msg):
    return json.dumps({
        "answer": "error",
        "comment": msg
    })

def result(r):
    return json.dumps({
        "answer": "result",
        "result": {
            "table": [[ {"x": "double"}, {"y": "double"} ]] + r
        }
    })

def main():

    try:

        if sys.argv[1] == '-i':

            with open('testt.json') as f:
                d = json.load(f)
                write(json.dumps(d, indent = 2))

        elif sys.argv[1] == '-r':

            textdata = raw_input()
            data = json.loads(textdata)

            if not len(data) or data[-1]['label'] != 'sintaylor':
                write(error('Unknown model'))
                sys.exit(1)

            params = data[0]['params']
            l = 0                   # левая граница
            r = params['r']         # правая граница
            n = params['n']         # количество шагов
            d = params['d']         # количество членов в разложении Тейлора
            h = float(r - l) / n    # шаг сетки по х
            res = []                # таблица резултатов

            while l <= r:
                y = sin_taylor(l, d)
                res.append([l, y])
                write(answer(l / r, data[-1]['label']))
                l += h
                time.sleep(0.1)

            write(result(res))

    except Exception, e:
        write(error('Fatal error: ' + str(e)))
        sys.exit(1)

if __name__ == '__main__':
    main()
