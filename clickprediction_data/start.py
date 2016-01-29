#!/usr/bin/python
from __future__ import division
from numpy import *

def main():
    training_data = genfromtxt('train.txt', delimiter=',')
    Y_train = training_data[:,0]
    X_train = training_data[:, 1:]
    Y_test = genfromtxt('test_label.txt', delimiter=',')
    X_test = genfromtxt('test.txt', delimiter=',')
    print('Susie')

if __name__ == '__main__':
    main()
