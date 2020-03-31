import redis

from includes import *

'''
python -m RLTest --test tests_tflite.py --module path/to/redisai.so
'''


def test_run_tflite_model(env):
    if not TEST_TFLITE:
        env.debugPrint("skipping {} since TEST_TFLITE=0".format(sys._getframe().f_code.co_name), force=True)
        return

    con = env.getConnection()

    test_data_path = os.path.join(os.path.dirname(__file__), 'test_data')
    model_filename = os.path.join(test_data_path, 'mnist_model_quant.tflite')
    wrong_model_filename = os.path.join(test_data_path, 'graph.pb')
    sample_filename = os.path.join(test_data_path, 'one.raw')

    with open(model_filename, 'rb') as f:
        model_pb = f.read()

    with open(model_filename, 'rb') as f:
        model_pb2 = f.read()

    with open(wrong_model_filename, 'rb') as f:
        wrong_model_pb = f.read()

    with open(sample_filename, 'rb') as f:
        sample_raw = f.read()

    ret = con.execute_command('AI.MODELSET', 'm', 'TFLITE', 'CPU', model_pb)
    env.assertEqual(ret, b'OK')

    ret = con.execute_command('AI.MODELGET', 'm')
    env.assertEqual(len(ret), 6)
    env.assertEqual(ret[-1], b'')

    ret = con.execute_command('AI.MODELSET', 'm', 'TFLITE', 'CPU', 'TAG', 'asdf', model_pb)
    env.assertEqual(ret, b'OK')

    ret = con.execute_command('AI.MODELGET', 'm')
    env.assertEqual(len(ret), 6)
    env.assertEqual(ret[-1], b'asdf')

    ret = con.execute_command('AI.TENSORSET', 'a', 'FLOAT', 1, 1, 28, 28, 'BLOB', sample_raw)
    env.assertEqual(ret, b'OK')

    ensureSlaveSynced(con, env)

    ret = con.execute_command('AI.MODELGET', 'm')
    env.assertEqual(len(ret), 6)
    # TODO: enable me
    # env.assertEqual(ret[0], b'TFLITE')
    # env.assertEqual(ret[1], b'CPU')

    try:
        con.execute_command('AI.MODELSET', 'm_1', 'TFLITE', model_pb)
    except Exception as e:
        exception = e
        env.assertEqual(type(exception), redis.exceptions.ResponseError)

    ret = con.execute_command('AI.MODELSET', 'm_2', 'TFLITE', 'CPU', model_pb2)
    ensureSlaveSynced(con, env)

    try:
        con.execute_command('AI.MODELSET', 'm_2', model_pb)
    except Exception as e:
        exception = e
        env.assertEqual(type(exception), redis.exceptions.ResponseError)

    try:
        con.execute_command('AI.MODELRUN', 'm_2', 'INPUTS', 'a', 'OUTPUTS')
    except Exception as e:
        exception = e
        env.assertEqual(type(exception), redis.exceptions.ResponseError)

    try:
        con.execute_command('AI.MODELRUN', 'm_2', 'INPUTS', 'a', 'b', 'c')
    except Exception as e:
        exception = e
        env.assertEqual(type(exception), redis.exceptions.ResponseError)

    try:
        con.execute_command('AI.MODELRUN', 'm_2', 'a', 'b', 'c')
    except Exception as e:
        exception = e
        env.assertEqual(type(exception), redis.exceptions.ResponseError)

    try:
        con.execute_command('AI.MODELRUN', 'm_2', 'OUTPUTS', 'c')
    except Exception as e:
        exception = e
        env.assertEqual(type(exception), redis.exceptions.ResponseError)

    try:
        con.execute_command('AI.MODELRUN', 'm', 'OUTPUTS', 'c')
    except Exception as e:
        exception = e
        env.assertEqual(type(exception), redis.exceptions.ResponseError)

    try:
        con.execute_command('AI.MODELRUN', 'm', 'INPUTS', 'a', 'b')
    except Exception as e:
        exception = e
        env.assertEqual(type(exception), redis.exceptions.ResponseError)

    try:
        con.execute_command('AI.MODELRUN', 'm', 'INPUTS', 'OUTPUTS')
    except Exception as e:
        exception = e
        env.assertEqual(type(exception), redis.exceptions.ResponseError)

    try:
        con.execute_command('AI.MODELRUN', 'm', 'INPUTS', 'a', 'OUTPUTS', 'b')
    except Exception as e:
        exception = e
        env.assertEqual(type(exception), redis.exceptions.ResponseError)

    con.execute_command('AI.MODELRUN', 'm', 'INPUTS', 'a', 'OUTPUTS', 'b', 'c')

    ensureSlaveSynced(con, env)

    tensor = con.execute_command('AI.TENSORGET', 'b', 'VALUES')
    value = tensor[-1][0]

    env.assertEqual(value, 1)


# TODO: Autobatch is tricky with TFLITE because TFLITE expects a fixed batch
#       size. At least we should constrain MINBATCHSIZE according to the
#       hard-coded dims in the tflite model.
def test_run_tflite_model_autobatch(env):
    if not TEST_PT:
        return

    con = env.getConnection()

    test_data_path = os.path.join(os.path.dirname(__file__), 'test_data')
    model_filename = os.path.join(test_data_path, 'mnist_model_quant.tflite')
    sample_filename = os.path.join(test_data_path, 'one.raw')

    with open(model_filename, 'rb') as f:
        model_pb = f.read()

    with open(sample_filename, 'rb') as f:
        sample_raw = f.read()

    try:
        ret = con.execute_command('AI.MODELSET', 'm', 'TFLITE', 'CPU',
                                  'BATCHSIZE', 2, 'MINBATCHSIZE', 2, model_pb)
    except Exception as e:
        exception = e
    env.assertEqual(type(exception), redis.exceptions.ResponseError)

    # env.assertEqual(ret, b'OK')

    # con.execute_command('AI.TENSORSET', 'a', 'FLOAT', 1, 1, 28, 28, 'BLOB', sample_raw)
    # con.execute_command('AI.TENSORSET', 'c', 'FLOAT', 1, 1, 28, 28, 'BLOB', sample_raw)

    # def run():
    #     con = env.getConnection()
    #     con.execute_command('AI.MODELRUN', 'm', 'INPUTS', 'c', 'OUTPUTS', 'd', 'd2')

    # t = threading.Thread(target=run)
    # t.start()

    # con.execute_command('AI.MODELRUN', 'm', 'INPUTS', 'a', 'OUTPUTS', 'b', 'b2')

    # tensor = con.execute_command('AI.TENSORGET', 'b', 'VALUES')
    # value = tensor[-1][0]

    # env.assertEqual(value, 1)

    # tensor = con.execute_command('AI.TENSORGET', 'd', 'VALUES')
    # value = tensor[-1][0]

    # env.assertEqual(value, 1)


def test_tflite_modelinfo(env):
    if not TEST_TFLITE:
        env.debugPrint("skipping {} since TEST_TFLITE=0".format(sys._getframe().f_code.co_name), force=True)
        return

    if DEVICE == "GPU":
        env.debugPrint("skipping {} since it's hanging CI".format(sys._getframe().f_code.co_name), force=True)
        return

    con = env.getConnection()
    test_data_path = os.path.join(os.path.dirname(__file__), 'test_data')
    model_filename = os.path.join(test_data_path, 'mnist_model_quant.tflite')
    sample_filename = os.path.join(test_data_path, 'one.raw')

    with open(model_filename, 'rb') as f:
        model_pb = f.read()

    with open(sample_filename, 'rb') as f:
        sample_raw = f.read()

    ret = con.execute_command('AI.MODELSET', 'mnist', 'TFLITE', 'CPU', model_pb)
    env.assertEqual(ret, b'OK')

    ret = con.execute_command('AI.TENSORSET', 'a', 'FLOAT', 1, 1, 28, 28, 'BLOB', sample_raw)
    env.assertEqual(ret, b'OK')

    ensureSlaveSynced(con, env)

    previous_duration = 0
    for call in range(1, 10):
        ret = con.execute_command('AI.MODELRUN', 'mnist', 'INPUTS', 'a', 'OUTPUTS', 'b', 'c')
        env.assertEqual(ret, b'OK')
        ensureSlaveSynced(con, env)

        info = con.execute_command('AI.INFO', 'mnist')
        info_dict_0 = info_to_dict(info)

        env.assertEqual(info_dict_0['KEY'], 'mnist')
        env.assertEqual(info_dict_0['TYPE'], 'MODEL')
        env.assertEqual(info_dict_0['BACKEND'], 'TFLITE')
        env.assertEqual(info_dict_0['DEVICE'], DEVICE)
        env.assertTrue(info_dict_0['DURATION'] > previous_duration)
        env.assertEqual(info_dict_0['SAMPLES'], call)
        env.assertEqual(info_dict_0['CALLS'], call)
        env.assertEqual(info_dict_0['ERRORS'], 0)

        previous_duration = info_dict_0['DURATION']

    res = con.execute_command('AI.INFO', 'mnist', 'RESETSTAT')
    env.assertEqual(res, b'OK')
    info = con.execute_command('AI.INFO', 'mnist')
    info_dict_0 = info_to_dict(info)
    env.assertEqual(info_dict_0['DURATION'], 0)
    env.assertEqual(info_dict_0['SAMPLES'], 0)
    env.assertEqual(info_dict_0['CALLS'], 0)
    env.assertEqual(info_dict_0['ERRORS'], 0)


def test_tflite_modelrun_disconnect(env):
    if not TEST_TFLITE:
        env.debugPrint("skipping {} since TEST_TFLITE=0".format(sys._getframe().f_code.co_name), force=True)
        return

    red = env.getConnection()
    test_data_path = os.path.join(os.path.dirname(__file__), 'test_data')
    model_filename = os.path.join(test_data_path, 'mnist_model_quant.tflite')
    sample_filename = os.path.join(test_data_path, 'one.raw')

    with open(model_filename, 'rb') as f:
        model_pb = f.read()

    with open(sample_filename, 'rb') as f:
        sample_raw = f.read()

    ret = red.execute_command('AI.MODELSET', 'mnist', 'TFLITE', 'CPU', model_pb)
    env.assertEqual(ret, b'OK')

    ret = red.execute_command('AI.TENSORSET', 'a', 'FLOAT', 1, 1, 28, 28, 'BLOB', sample_raw)
    env.assertEqual(ret, b'OK')

    ensureSlaveSynced(red, env)

    ret = send_and_disconnect(('AI.MODELRUN', 'mnist', 'INPUTS', 'a', 'OUTPUTS', 'b', 'c'), red)
    env.assertEqual(ret, None)