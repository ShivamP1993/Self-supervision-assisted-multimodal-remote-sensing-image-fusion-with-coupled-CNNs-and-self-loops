# Function to perform one hot encoding of the class labels

def my_ohc(lab_arr):
  lab_arr_unique =  np.unique(lab_arr)
  r,c = lab_arr.shape
  r_u  = lab_arr_unique.shape
  one_hot_enc = np.zeros((r,r_u[0]), dtype = 'float')

  for i in range(r):
    for j in range(r_u[0]):
      if lab_arr[i,0] == lab_arr_unique[j]:
        one_hot_enc[i,j] = 1

  return one_hot_enc

# Function that takes the confusion matrix as input and
# calculates the overall accuracy, producer's accuracy, user's accuracy,
# Cohen's kappa coefficient and standard deviation of
# Cohen's kappa coefficient

def accuracies(cm):
  import numpy as np
  num_class = np.shape(cm)[0]
  n = np.sum(cm)

  P = cm/n
  ovr_acc = np.trace(P)

  p_plus_j = np.sum(P, axis = 0)
  p_i_plus = np.sum(P, axis = 1)

  usr_acc = np.diagonal(P)/p_i_plus
  prod_acc = np.diagonal(P)/p_plus_j

  theta1 = np.trace(P)
  theta2 = np.sum(p_plus_j*p_i_plus)
  theta3 = np.sum(np.diagonal(P)*(p_plus_j + p_i_plus))
  theta4 = 0
  for i in range(num_class):
    for j in range(num_class):
      theta4 = theta4+P[i,j]*(p_plus_j[i]+p_i_plus[j])**2

  kappa = (theta1-theta2)/(1-theta2)

  t1 = theta1*(1-theta1)/(1-theta2)**2
  t2 = 2*(1-theta1)*(2*theta1*theta2-theta3)/(1-theta2)**3
  t3 = ((1-theta1)**2)*(theta4 - 4*theta2**2)/(1-theta2)**4

  s_sqr = (t1+t2+t3)/n

  return ovr_acc, usr_acc, prod_acc, kappa, s_sqr

# Import Relevant libraries and classes
import scipy.io as sio
import numpy as np
import tqdm
from sklearn.decomposition import PCA
import tensorflow as tf
keras = tf.keras
from keras import backend as K
from keras import regularizers
from keras.models import Model, Sequential
from keras.layers import Dense, Input, Dropout, Permute, TimeDistributed, MultiHeadAttention, LayerNormalization
from keras.layers import Conv2D, Flatten, Lambda, Conv3D, Conv3DTranspose, BatchNormalization, Conv1D, Activation
from keras.layers import Reshape, Conv2DTranspose, Concatenate, Multiply, Add, MaxPooling2D,GlobalAveragePooling1D
from keras.layers import MaxPooling3D, GlobalAveragePooling2D, GlobalMaxPooling2D, DepthwiseConv2D, Layer
from keras.datasets import mnist
from keras.losses import mse, binary_crossentropy
from keras.callbacks import LearningRateScheduler, ModelCheckpoint
import math
from keras import backend as K
from sklearn.metrics import confusion_matrix
from keras.losses import MeanSquaredError

train_patches = np.load('data/train_patches.npy')
test_patches = np.load('data/test_patches.npy')

train_labels = np.load('data/train_labels.npy')-1
test_labels = np.load('data/test_labels.npy')-1

tr90 = np.empty([2832,11,11,145], dtype = 'float32')
tr180 = np.empty([2832,11,11,145], dtype = 'float32')
tr270 = np.empty([2832,11,11,145], dtype = 'float32')

for i in tqdm.tqdm(range(2832)):
  tr90[i,:,:,:] = np.rot90(train_patches[i,:,:,:])
  tr180[i,:,:,:] = np.rot90(tr90[i,:,:,:])
  tr270[i,:,:,:] = np.rot90(tr180[i,:,:,:])

train_patches = np.concatenate([train_patches, tr90, tr180, tr270], axis = 0)
train_labels = np.concatenate([train_labels,train_labels,train_labels,train_labels], axis = 0)

def my_conv(x,l):

  c1 = l(x)
  c1 = BatchNormalization()(c1)

  return c1

def my_cnn(xH,xL,k):

  xH1 = Reshape([11,11,12,12])(xH)

  c1_3d = Conv3D(12, (3,3,3), strides=1, padding='SAME', use_bias=True,
                 kernel_initializer='glorot_normal', activation = 'relu')(xH1)

  c_rshp = Reshape([11,11,144])(c1_3d)

  ch1 = Conv2D(64, k, strides=1, padding='SAME', use_bias=True,
                   kernel_initializer='glorot_normal', activation = 'relu')(c_rshp)

  cl1 = Conv2D(64, k, strides=1, padding='SAME', use_bias=True,
                   kernel_initializer='glorot_normal', activation = 'relu')(xL)

  ## Shared layers

  l1 = Conv2D(64, k, strides=1, padding='SAME', use_bias=True, kernel_initializer='glorot_normal', activation = 'relu')
  l2 = Conv2D(64, k, strides=1, padding='SAME', use_bias=True, kernel_initializer='glorot_normal', activation = 'relu')
  l3 = Conv2D(64, k, strides=1, padding='SAME', use_bias=True, kernel_initializer='glorot_normal', activation = 'relu')
  l4 = Conv2D(64, k, strides=1, padding='SAME', use_bias=True, kernel_initializer='glorot_normal', activation = 'relu')

  # Stage 1 HSI

  cv1 = my_conv(ch1, l1)
  c1 = Add()([ch1,cv1])
  cv2 = my_conv(c1, l2)
  c2 = Add()([ch1,cv1,cv2])
  cv3 = my_conv(c2, l3)
  c3 = Add()([ch1,cv1,cv2,cv3])
  cv4 = my_conv(c3, l4)

  # Stage 1 LiDAR

  cvl1 = my_conv(cl1, l1)
  cl1 = Add()([cl1,cvl1])
  cvl2 = my_conv(cl1, l2)
  cl2 = Add()([cl1,cvl1,cvl2])
  cvl3 = my_conv(cl2, l3)
  cl3 = Add()([cl1,cvl1,cvl2,cvl3])
  cvl4 = my_conv(cl3, l4)

  # Stage 2 HSI

  c4 = Add()([cv2,cv3,cv4])
  cv1 = my_conv(c4, l1)
  c5 = Add()([cv1,cv3,cv4])
  cv2 = my_conv(c5, l2)
  c6 = Add()([cv1,cv2,cv4])
  cv3 = my_conv(c6, l3)
  c7 = Add()([cv1,cv2,cv3])
  cv4 = my_conv(c7, l4)

  # Stage 2 LiDAR

  cl4 = Add()([cvl2,cvl3,cvl4])
  cvl1 = my_conv(cl4, l1)
  cl5 = Add()([cvl1,cvl3,cvl4])
  cvl2 = my_conv(cl5, l2)
  cl6 = Add()([cvl1,cvl2,cvl4])
  cvl3 = my_conv(cl6, l3)
  cl7 = Add()([cvl1,cvl2,cvl3])
  cvl4 = my_conv(cl7, l4)

  conc1 = Concatenate(axis = 3)([cv1,cv2,cv3,cv4])
  gap1 = GlobalAveragePooling2D()(conc1)

  concl1 = Concatenate(axis = 3)([cvl1,cvl2,cvl3,cvl4])
  gapl1 = GlobalAveragePooling2D()(concl1)

  cat1 = Concatenate(axis = 1)([gap1, gapl1])
  d1 = Dense(32, activation = 'relu')(cat1)

  return d1, gap1, gapl1

def ext(xH, xL):

  gp3, h3, l3 = my_cnn(xH,xL,3)
  gp5, h5, l5 = my_cnn(xH,xL,5)

  gp = Concatenate(axis = 1)([gp3, gp5])
  gph = Concatenate(axis = 1)([h3, h5])
  gpl = Concatenate(axis = 1)([l3, l5])

  c6 =  Dense(15, activation = 'softmax')(gp)
  return Reshape([15])(c6), gph, gpl

def rec_hs(x):

  x = Dense(64, activation = 'relu')(x)
  x = Reshape([1,1,64])(x)
  c1 = Conv2DTranspose(64, 3, strides=1, padding='VALID', use_bias=True, kernel_initializer='glorot_normal', activation = 'relu')(x)
  c2 = Conv2DTranspose(64, 3, strides=1, padding='SAME', use_bias=True, kernel_initializer='glorot_normal', activation = 'relu')(c1)
  r1 = Concatenate(axis = 3)([c1,c2])

  c3 = Conv2DTranspose(64, 3, strides=1, padding='VALID', use_bias=True, kernel_initializer='glorot_normal', activation = 'relu')(r1)
  c4 = Conv2DTranspose(64, 3, strides=1, padding='SAME', use_bias=True, kernel_initializer='glorot_normal', activation = 'relu')(c3)
  r2 = Concatenate(axis = 3)([c3,c4])

  c5 = Conv2DTranspose(64, 3, strides=1, padding='VALID', use_bias=True, kernel_initializer='glorot_normal', activation = 'relu')(r2)
  c6 = Conv2DTranspose(64, 3, strides=1, padding='SAME', use_bias=True, kernel_initializer='glorot_normal', activation = 'relu')(c5)
  r3 = Concatenate(axis = 3)([c5,c6])

  c7 = Conv2DTranspose(64, 3, strides=1, padding='VALID', use_bias=True, kernel_initializer='glorot_normal', activation = 'relu')(r3)
  c8 = Conv2DTranspose(1, 3, strides=1, padding='VALID', use_bias=True, kernel_initializer='glorot_normal', activation = 'sigmoid')(c7)

  return c8

def rec_lid(x):

  x = Dense(64, activation = 'relu')(x)
  x = Reshape([1,1,64])(x)
  c1 = Conv2DTranspose(64, 3, strides=1, padding='VALID', use_bias=True, kernel_initializer='glorot_normal', activation = 'relu')(x)
  c2 = Conv2DTranspose(64, 3, strides=1, padding='SAME', use_bias=True, kernel_initializer='glorot_normal', activation = 'relu')(c1)
  r1 = Concatenate(axis = 3)([c1,c2])

  c3 = Conv2DTranspose(64, 3, strides=1, padding='VALID', use_bias=True, kernel_initializer='glorot_normal', activation = 'relu')(r1)
  c4 = Conv2DTranspose(64, 3, strides=1, padding='SAME', use_bias=True, kernel_initializer='glorot_normal', activation = 'relu')(c3)
  r2 = Concatenate(axis = 3)([c3,c4])

  c5 = Conv2DTranspose(64, 3, strides=1, padding='VALID', use_bias=True, kernel_initializer='glorot_normal', activation = 'relu')(r2)
  c6 = Conv2DTranspose(64, 3, strides=1, padding='SAME', use_bias=True, kernel_initializer='glorot_normal', activation = 'relu')(c5)
  r3 = Concatenate(axis = 3)([c5,c6])

  c7 = Conv2DTranspose(64, 3, strides=1, padding='VALID', use_bias=True, kernel_initializer='glorot_normal', activation = 'relu')(r3)
  c8 = Conv2DTranspose(144, 3, strides=1, padding='VALID', use_bias=True, kernel_initializer='glorot_normal', activation = 'sigmoid')(c7)

  return c8

def my_rmse(y_true, y_pred, lam1):
  error = y_true-y_pred
  sqr_error = K.square(error)
  mean_sqr_error = K.mean(sqr_error)
  sqrt_mean_sqr_error = K.sqrt(mean_sqr_error)
  sqrt_mean_sqr_error = Lambda(lambda x: x * lam1)(sqrt_mean_sqr_error)
  return sqrt_mean_sqr_error

xH = Input(shape=(11,11,144), name='inputH')
xL = Input(shape=(11,11,1), name='inputL')

outfinal, gph, gpl = ext(xH, xL)

hs1 = rec_hs(gph)
lid1 = rec_lid(gpl)

optim = keras.optimizers.Nadam(0.00006)
model = Model([xH,xL], outfinal, name = 'model')

model.add_loss(my_rmse(xL, hs1,1))
model.add_loss(my_rmse(xH, lid1,1))

# Compiling the model
model.compile(loss=['categorical_crossentropy'], optimizer=optim, metrics=['accuracy'])
model.summary()

keras.utils.plot_model(model)

# This function keeps the initial learning rate for the first ten epochs
# and decreases it exponentially after that.
def scheduler(epoch, lr):
  if epoch < 20:
    return lr
  else:
    return lr * tf.math.exp(-0.005)

cb1 = LearningRateScheduler(scheduler)
cb2 = ModelCheckpoint(
    'models/model', monitor='val_accuracy', verbose=0,
    save_best_only=True,
    save_weights_only=False, mode='auto', save_freq='epoch')

history = model.fit(x = [train_patches[:,:,:,0:144], train_patches[:,:,:,144:145]],
                  y = my_ohc(np.expand_dims(train_labels, axis = 1)),
          validation_data = ([test_patches[:,:,:,0:144], test_patches[:,:,:,144:145]],
                             my_ohc(np.expand_dims(test_labels, axis = 1))),
                  epochs=500, batch_size = 64, callbacks = [cb1, cb2], verbose = 1)
