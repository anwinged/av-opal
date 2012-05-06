#! coding: utf-8

# Тестовое приложение для проекта Opal
# Вычисление значений синуса по формулам Тейлора
# Вычисляет значения для указанного диапазона
#  с заданной точностью и нужным количеством шагов

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

def result(s, t):
    return json.dumps({
        "answer": "result",
        "result": {
            "data":  s,
            "table": t
        }})

def serie(n, d, h, l = 0):
    for i in xrange(n + 1):
        y = sin_taylor(l, d)
        yield (l, y)
        l += h
        # time.sleep(0.002)

def main():

    try:

        if sys.argv[1] == '-i':

            with open('testt.json') as f:
                d = json.load(f)
                write(json.dumps(d, indent = 2))

        elif sys.argv[1] == '-r':

            textdata = raw_input()
            data = json.loads(textdata)

            params = data[0]['params']
            r = params['r']         # правая граница
            n = params['n']         # количество шагов
            d = params['d']         # количество членов в разложении Тейлора
            h = r / n
            res = []                # таблица резултатов

            label = data[-1]['label']
            sum = 0

            if   label == 'sintaylor':
                for x, y in serie(n, d, h):
                    res.append([x, y])
                    write(answer(x / r, label))
                write(result({},
                    [[ ['x', 'double'], [ 'y', 'double' ] ]] + res))

            elif label == 'left':
                for x, y in serie(n - 1, d, h):
                    s = y * h
                    res.append([x, y, s])
                    write(answer(x / r, label))
                    sum += s
                write(result(
                    { 'sum': sum },
                    [[ ['x', 'double'], [ 'y', 'double' ], [ 's', 'double', 'Delta sum' ] ]] + res))

            elif label == 'right':
                for x, y in serie(n - 1, d, h, h):
                    s = y * h
                    res.append([x, y, s])
                    write(answer(x / r, label))
                    sum += s
                write(result(
                    { 'sum': sum },
                    [[ ['x', 'double'], [ 'y', 'double' ], [ 's', 'double' ] ]] + res))

            elif label == 'trapezium':
                prev = 0
                for x, y in serie(n, d, h):
                    s = 0.5 * (y + prev) * h
                    res.append([x, y, s])
                    write(answer(x / r, label))
                    sum += s
                    prev = y
                write(result(
                    { 'sum': sum },
                    [[ ['x', 'double'], [ 'y', 'double' ], [ 's', 'double' ] ]] + res))


    except Exception, e:
        write(error('Fatal error: ' + str(e)))
        sys.exit(1)

if __name__ == '__main__':
    main()
