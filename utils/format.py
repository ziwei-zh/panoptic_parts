
import numpy as np
import tensorflow as tf
# import torch as T

# Functions that start with underscore (_) should be considered as internal.
# All other functions belong to the public API.
# Arguments and functions defined with the preffix experimental_ may be changed
# and are not backward-compatible.

# PUBLIC_API = [decode_uids, encode_ids]

def decode_uids(uids,
                experimental_return_sids_iids=False,
                experimental_return_sids_pids=False):
  """
  Given a numpy np.ndarray, a TF tensor, a Python int, or a np.int32
  representing uids according to the hierarchical format described
  in README, this function returns element-wise
  the semantic ids (sids), instance ids (iids), and part ids (pids).
  Optionally (experimental for now), returns the sids_iids and sids_pids as well.

  sids_iids represent the semantic-instance-level (two-level) labeling,
  e.g., sids_iids(Cityscapes-Panoptic-Parts) = Cityscapes-Original.

  sids_pids = sids * 100 + max(pids, 0) and represent the semantic-part-level labeling,
  e.g., sids_pids(23_003_04) = 23_04.

  Args:
    uids: tf.Tensor of dtype tf.int32 and arbitrary shape,
          or tf.ndarray of dtype np.int32 and arbitrary shape,
          or Python int,
          or np.int32 int,
          with elements according to hierarchical format (see README).

  Return:
    sids, iids, pids: same type and shape as uids, with -1 for not relevant pixels.
  
    sids will have no -1.
    iids will have -1 for pixels labeled with sids only.
    pids will have -1 for pixels labeled with sids or sids_iids only.
  
    if experimental_return_sids_iids:
      sids_iids: same type and shape as uids, will have no -1.
    if experimental_return_sids_pids:
      sids_pids: same type and shape as uids, will have no -1.
  """

  if isinstance(uids, np.ndarray):
    if uids.dtype != np.int32:
      raise TypeError(f'{uids.dtype} is an unsupported dtype of np.ndarray uids.')
    where = np.where
    ones_like = np.ones_like
    divmod_ = np.divmod
    maximum = np.maximum
    dtype = np.int32
  elif isinstance(uids, tf.Tensor):
    if uids.dtype != tf.int32:
      raise TypeError(f'{uids.dtype} is an unsupported dtype of tf.Tensor uids.')
    where = tf.where
    ones_like = tf.ones_like
    divmod_ = lambda x, y: (x // y, x % y)
    maximum = tf.maximum
    dtype = lambda x: x
  elif isinstance(uids, (int, np.int32)):
    where = lambda cond, true_br, false_br: true_br if cond else false_br
    ones_like = lambda the_like: type(the_like)(1)
    divmod_ = divmod
    maximum = max
    dtype = (lambda x: x) if isinstance(uids, int) else np.int32
  else:
    raise TypeError(f'{type(uids)} is an unsupported type of uids.')

  # TODO(panos): find better solution, e.g. convert to necessary type only before returning?
  # explanations for using dtype, np.asarray that should be not needed in the following lines
  # dtype: numpy implicitly converts Python int literals in np.int64, we need np.int32
  # np.asarray: numpy implicitly converts ndarray with one element to np.int32 (which is not
  #   ndarray) moreover dtypes are implicitly converted to np.int64 for arithmetic operations

  # pad uids to uniform 7-digit length
  uids_padded = where(uids <= 99_999,
                      where(uids <= 99, uids * dtype(10**5), uids * dtype(10**2)),
                      uids)
  # split uids to components (sids, iids, pids) from right to left
  sids_iids, pids = divmod_(uids_padded, dtype(10**2))
  if isinstance(uids, np.ndarray):
    sids_iids = np.asarray(sids_iids, dtype=np.int32)
  sids, iids = divmod_(sids_iids, dtype(10**3))
  if isinstance(uids, np.ndarray):
    sids = np.asarray(sids, dtype=np.int32)
  invalid_ids = ones_like(uids) * dtype(-1)
  # set invalid ids
  iids = where(uids <= 99, invalid_ids, iids)
  pids = where(uids <= 99_999, invalid_ids, pids)

  returns = (sids, iids, pids)

  if experimental_return_sids_iids:
    sids_iids = where(uids <= 99_999, uids, sids_iids)
    returns += (sids_iids,)

  if experimental_return_sids_pids:
    sids_pids = sids * dtype(10**2) + maximum(pids, dtype(0))
    if isinstance(uids, np.ndarray):
      sids_pids = np.asarray(sids_pids, dtype=np.int32)
    returns += (sids_pids,)

  return returns

def encode_ids(sids, iids, pids):
  """
  Given semantic ids (sids), instance ids (iids), and part ids (pids)
  this function encodes them element-wise to uids
  according to the hierarchical format described in README.

  This function is the opposite of decode_uids, i.e.,
  uids = encode_ids(decode_uids(uids)).

  Note: this function is still not fully tested.

  Args:
    sids, iids, pids: all of the same type with -1 for non-relevant pixels with
      elements according to hierarchical format (see README). Can be:
      tf.Tensor of dtype tf.int32 and arbitrary shape,
      tf.ndarray of dtype np.int32 and arbitrary shape,
      Python int,
      np.int32 int.

  Return:
    uids: same type and shape as the args according to hierarchical format (see README).
  """

  if type(sids) is not type(iids) and type(iids) is not type(pids):
    raise ValueError(
        f"All arguments must have the same type, not {(*map(type, (sids, iids, pids)),)}")
  if isinstance(sids, np.ndarray):
    if sids.dtype != np.int32:
      raise TypeError(f'{sids.dtype} is an unsupported dtype of np.ndarray uids.')
    where = np.where
  elif isinstance(sids, tf.Tensor):
    if sids.dtype != tf.int32:
      raise TypeError(f'{sids.dtype} is an unsupported dtype of tf.Tensor uids.')
    where = tf.where
  elif isinstance(sids, (int, np.int32, np.int64)):
    # assert all([0 <= sids <= 99, 0 <= iids <= 999, 0 <= pids <= 99]), f"{(sids, iids, pids)}"
    where = lambda cond, true_br, false_br: true_br if cond else false_br
  else:
    raise TypeError(f'{type(sids)} is an unsupported type of ids.')

  sids_iids = where(iids < 0, sids, sids * 10**3 + iids)
  uids = where(pids < 0, sids_iids, sids_iids * 10**2 + pids)

  return uids
