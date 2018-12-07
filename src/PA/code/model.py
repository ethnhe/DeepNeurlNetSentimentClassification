#-*- coding: utf-8 -*-
#author: Zhen Wu

import tensorflow as tf
# from tensorflow.python.ops import rnn
from tensorflow.contrib import rnn
tf.nn.rnn_cell = rnn

class huapahata(object):

    def __init__(self, max_sen_len, max_doc_len, class_num, embedding_file,
            embedding_dim, hidden_size, user_num, product_num, helpfulness_num, time_num):
        self.max_sen_len = max_sen_len
        self.max_doc_len = max_doc_len
        self.class_num = class_num
        self.embedding_file = embedding_file
        self.embedding_dim = embedding_dim
        self.hidden_size = hidden_size
        self.user_num = user_num
        self.product_num = product_num
        self.helpfulness_num = helpfulness_num
        self.time_num = time_num

        with tf.name_scope('input'):
            self.userid = tf.placeholder(tf.int32, [None], name="user_id")
            self.productid = tf.placeholder(tf.int32, [None], name="product_id")
            self.helpfulnessid = tf.placeholder(tf.int32, [None], name="helpfulness_id")
            self.timeid = tf.placeholder(tf.int32, [None], name="time_id")
            self.input_x = tf.placeholder(tf.int32, [None, self.max_doc_len, self.max_sen_len], name="input_x")
            self.input_y = tf.placeholder(tf.float32, [None, self.class_num], name="input_y")
            self.sen_len = tf.placeholder(tf.int32, [None, self.max_doc_len], name="sen_len")
            self.doc_len = tf.placeholder(tf.int32, [None], name="doc_len")

        with tf.name_scope('weights'):
            self.weights = {
                'softmax': tf.Variable(tf.random_uniform([2 * self.hidden_size, self.class_num], -0.01, 0.01)),

                'p_softmax': tf.Variable(tf.random_uniform([2 * self.hidden_size, self.class_num], -0.01, 0.01)),
                'p_wh_1': tf.Variable(tf.random_uniform([2 * self.hidden_size, 2 * self.hidden_size], -0.01, 0.01)),
                'p_v_1': tf.Variable(tf.random_uniform([2 * self.hidden_size, 1], -0.01, 0.01)),
                'p_wh_2': tf.Variable(tf.random_uniform([2 * self.hidden_size, 2 * self.hidden_size], -0.01, 0.01)),
                'p_v_2': tf.Variable(tf.random_uniform([2 * self.hidden_size, 1], -0.01, 0.01)),

                'wp_1': tf.Variable(tf.random_uniform([2 * self.hidden_size, 2 * self.hidden_size], -0.01, 0.01)),
                'wp_2': tf.Variable(tf.random_uniform([2 * self.hidden_size, 2 * self.hidden_size], -0.01, 0.01)),
            }

        with tf.name_scope('biases'):
            self.biases = {
                'softmax': tf.Variable(tf.random_uniform([self.class_num], -0.01, 0.01)),

                'p_softmax': tf.Variable(tf.random_uniform([self.class_num], -0.01, 0.01)),
                'p_wh_1': tf.Variable(tf.random_uniform([2 * self.hidden_size], -0.01, 0.01)),
                'p_wh_2': tf.Variable(tf.random_uniform([2 * self.hidden_size], -0.01, 0.01)),

            }

        with tf.name_scope('embedding'):
            self.word_embedding = tf.constant(self.embedding_file, name="word_embedding", dtype=tf.float32)
            self.x = tf.nn.embedding_lookup(self.word_embedding, self.input_x)
            self.user_embedding = tf.Variable(tf.random_uniform([self.user_num, 2*self.hidden_size], -0.01, 0.01), dtype=tf.float32)
            self.product_embedding = tf.Variable(tf.random_uniform([self.product_num, 2*self.hidden_size], -0.01, 0.01), dtype=tf.float32)
            self.helpfulness_embedding = tf.Variable(tf.random_uniform([self.helpfulness_num, 2*self.hidden_size], -0.01, 0.01), dtype=tf.float32)
            self.time_embedding = tf.Variable(tf.random_uniform([self.time_num, 2*self.hidden_size], -0.01, 0.01), dtype=tf.float32)
            self.user = tf.nn.embedding_lookup(self.user_embedding, self.userid)
            self.product = tf.nn.embedding_lookup(self.product_embedding, self.productid)
            self.helpfulness = tf.nn.embedding_lookup(self.helpfulness_embedding, self.helpfulnessid)
            self.time = tf.nn.embedding_lookup(self.time_embedding, self.timeid)


    def softmax(self, inputs, length, max_length):
        inputs = tf.cast(inputs, tf.float32)
        inputs = tf.exp(inputs)
        length = tf.reshape(length, [-1])
        mask = tf.reshape(tf.cast(tf.sequence_mask(length, max_length), tf.float32), tf.shape(inputs))
        inputs *= mask
        _sum = tf.reduce_sum(inputs, reduction_indices=2, keep_dims=True) + 1e-9
        return inputs / _sum


    def product_attention(self):
        inputs = tf.reshape(self.x, [-1, self.max_sen_len, self.embedding_dim])
        sen_len = tf.reshape(self.sen_len, [-1])
        with tf.name_scope('p_word_encode'):
            outputs, state = tf.nn.bidirectional_dynamic_rnn(
                cell_fw=tf.nn.rnn_cell.LSTMCell(self.hidden_size, forget_bias=1.0),
                cell_bw=tf.nn.rnn_cell.LSTMCell(self.hidden_size, forget_bias=1.0),
                inputs=inputs,
                sequence_length=sen_len,
                dtype=tf.float32,
                scope='p_word'
            )
            outputs = tf.concat(outputs, 2)

        batch_size = tf.shape(outputs)[0]
        with tf.name_scope('p_word_attention'):
            output = tf.reshape(outputs, [-1, 2 * self.hidden_size])
            u = tf.matmul(output, self.weights['p_wh_1']) + self.biases['p_wh_1']
            u = tf.reshape(u, [-1, self.max_doc_len*self.max_sen_len, 2*self.hidden_size])
            u += tf.matmul(self.product, self.weights['wp_1'])[:,None,:]
            u = tf.tanh(u)
            u = tf.reshape(u, [-1, 2 * self.hidden_size])
            alpha = tf.reshape(tf.matmul(u, self.weights['p_v_1']),
                               [batch_size, 1, self.max_sen_len])
            alpha = self.softmax(alpha, self.sen_len, self.max_sen_len)
            outputs = tf.matmul(alpha, outputs)


        outputs = tf.reshape(outputs, [-1, self.max_doc_len, 2 * self.hidden_size])
        with tf.name_scope('p_sentence_encode'):
            outputs, state = tf.nn.bidirectional_dynamic_rnn(
                cell_fw=tf.nn.rnn_cell.LSTMCell(self.hidden_size, forget_bias=1.0),
                cell_bw=tf.nn.rnn_cell.LSTMCell(self.hidden_size, forget_bias=1.0),
                inputs=outputs,
                sequence_length=self.doc_len,
                dtype=tf.float32,
                scope='p_sentence'
            )
            outputs = tf.concat(outputs, 2)

        batch_size = tf.shape(outputs)[0]
        with tf.name_scope('p_sentence_attention'):
            output = tf.reshape(outputs, [-1, 2 * self.hidden_size])
            u = tf.matmul(output, self.weights['p_wh_2']) + self.biases['p_wh_2']
            u = tf.reshape(u, [-1, self.max_doc_len, 2*self.hidden_size])
            u += tf.matmul(self.product, self.weights['wp_2'])[:,None,:]
            u = tf.tanh(u)
            u = tf.reshape(u, [-1, 2*self.hidden_size])
            alpha = tf.reshape(tf.matmul(u, self.weights['p_v_2']),
                               [batch_size, 1, self.max_doc_len])
            alpha = self.softmax(alpha, self.doc_len, self.max_doc_len)
            outputs = tf.matmul(alpha, outputs)

        with tf.name_scope('p_softmax'):
            self.p_doc = tf.reshape(outputs, [batch_size, 2 * self.hidden_size])
            self.p_scores = tf.matmul(self.p_doc, self.weights['p_softmax']) + self.biases['p_softmax']
            self.p_predictions = tf.argmax(self.p_scores, 1, name="p_predictions")

        with tf.name_scope("p_loss"):
            losses = tf.nn.softmax_cross_entropy_with_logits(logits=self.p_scores, labels=self.input_y)
            self.p_loss = tf.reduce_mean(losses)

        with tf.name_scope("p_accuracy"):
            correct_predictions = tf.equal(self.p_predictions, tf.argmax(self.input_y, 1))
            self.p_correct_num = tf.reduce_sum(tf.cast(correct_predictions, dtype=tf.int32))
            self.p_accuracy = tf.reduce_mean(tf.cast(correct_predictions, "float"), name="p_accuracy")



    def build_model(self):
        # self.user_attention()
        self.product_attention()
        # self.helpfulness_attention()
        # self.time_attention()

        with tf.name_scope('softmax'):
            outputs = tf.concat([self.p_doc], 1)
            self.scores = tf.matmul(outputs, self.weights['softmax']) + self.biases['softmax']
            self.predictions = tf.argmax(self.scores, 1, name="predictions")

        with tf.name_scope("loss"):
            losses = tf.nn.softmax_cross_entropy_with_logits(logits=self.scores, labels=self.input_y)
            self.loss = tf.reduce_mean(losses)

        with tf.name_scope("metrics"):
            correct_predictions = tf.equal(self.predictions, tf.argmax(self.input_y, 1))
            self.mse = tf.reduce_sum(tf.square(self.predictions - tf.argmax(self.input_y, 1)), name="mse")
            self.correct_num = tf.reduce_sum(tf.cast(correct_predictions, dtype=tf.int32), name="correct_num")
            self.accuracy = tf.reduce_mean(tf.cast(correct_predictions, "float"), name="accuracy")
