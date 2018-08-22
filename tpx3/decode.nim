
#import bitarray
import strformat
import tables
import math
# a simple Nim module, which performs decoding of the data sent by the FPGA
# *`fast`*

import random

type
  BitArray[T: static[int]] = object
    data: array[T, bool]

  ReturnData*[T: static[int]] = object
    ar*: array[T, uint64]
    len*: uint8

const headers = {0b101.uint16, 0b111, 0b110, 0b100, 0b011}

const headerMap = { "Acquisition" : 0b101.uint16,
                    "StopMatrix"  : 0b111.uint16,
                    "CTPR"        : 0b110.uint16,
                    "PCR"         : 0b100.uint16,
                    "Control"     : 0b011.uint16  }.toTable()


proc len(b: BitArray): int =
  b.data.len

template `^^`(s, i: untyped): untyped =
  (when i is BackwardsIndex: s.len - int(i) else: int(i))

proc createBitarray(size: static[int]): BitArray[size] =
  for i in 0 ..< size:
    result.data[i] = false

proc `[]=`*[T, U](b: var BitArray, inds: HSlice[T, U], val: SomeInteger) =
    let iStart = b ^^ inds.a
    let iEnd   = b ^^ inds.b
    let nInds = iEnd - iStart + 1

    if nInds > b.len:
      raise newException(IndexError, &"Slice of {inds} is out of range for BitArray of size {b.len}")
    if val.uint64 > (2 ^ nInds).uint64:
      raise newException(ValueError, &"Value of {val} is too large for {nInds} bits slice! " &
                                     &"Max size is {2 ^ nInds}")

    var m = 0
    var mval = val.uint
    for x in iStart .. iEnd:
      let isBitOne = (mval and 1.uint).bool
      #echo (1 shl m).repr
      #echo "Working on bit ", x, " with m ", mval, " is one ", isBitOne
      b.data[x] = if isBitOne: true else: false
      #inc m
      mval = mval shr 1
    #echo b

proc `[]=`[T: not HSlice, U: SomeInteger | bool](b: var BitArray, ind: T, val: U) =
    when val is SomeInteger:
      let boolVal = if val == 1: true else: false
    elif val is bool:
      let boolVal = val
    let i = b ^^ ind
    b.data[i] = boolVal

proc `[]`[T: BackwardsIndex | SomeInteger](b: BitArray, ind: T): uint =
  let i = b ^^ ind
  if i >= b.len:
    raise newException(IndexError , &"Index of value {i} is out of range for BitArray of size {b.len}")
  result = if b.data[i] == false: 0.uint else: 1.uint

proc `[]`[T, U](b: BitArray, inds: HSlice[T, U]): uint =
  if inds.len > b.len:
    raise newException(IndexError, &"Slice of {inds} is out of range for BitArray of size {b.len}")
  let iStart = b ^^ inds.a
  let iEnd   = b ^^ inds.b
  var m = 0
  for x in iStart .. iEnd:
    if b[x] == 1.uint:
      result += (2 ^ m).uint
    inc m

proc printBytes*(ba: BitArray, asBytes = false): string =
  ## prints the BitArray as a list of individual bytes
  result = newStringOfCap(8 * ba.len + 50)
  result = "["
  let nbytes = ba.len div 8
  if asBytes == false:
    for i in 0 ..< nbytes:
      for j in 0 ..< 8:
        let ind = (i * 8 + j).int
        result.add($(ba[ind]))
      if i != nbytes - 1:
        result.add ", "
    result.add "]"
  else:
    result = $(ba.toByteList)

proc `$`(b: BitArray): string =
  b.printBytes

proc toByteList(b: BitArray): seq[uint] =
  ## returns a seq of bytes based for the given `BitArray`
  ## Notes: needs to be a BitArray of size N bytes. If not, last
  ## elements are dropped
  let nbytes = b.len div 8
  for i in 0 ..< nbytes:
    let ind = i * 8
    result.add b[ind .. ind + 7]

proc bitwordToByteSeq(val: SomeInteger, size: static[int]): seq[uint] =
  var b = createBitarray(size)
  b[0 ..< size] = val
  result = b.toByteList

proc decode*(data: openArray[uint64]) {.exportc, dynlib.} =
  ## get the header and check for type

  for d in data:
    var header: uint16
    if ((d shr 47) and 1).bool:
      # if first bit is 1, small header
      header = (d shr 44).uint16
    else:
      header = (d shr 40).uint16

    if (header shr 5) == headerMap["Acquisition"]:
      echo "It's Acquisition!"
    elif (header shr 5) == headerMap["StopMatrix"]:
      echo "It's StopMatrix!"
    elif (header shr 5) == headerMap["CTPR"]:
      echo "It's CTPR!"
    elif (header shr 5) == headerMap["PCR"]:
      echo "It's PCR"
    elif (header shr 5) == headerMap["Control"]:
      echo "It's Control"
    else:
      echo "It's hopefully periphery! ", header

proc decode_fpga*(data: openArray[uint32], buffer: var openArray[uint64]) {.exportc, dynlib.} =

  assert data.len mod 2 == 0, "Missing one 32 bit subword of a 48 bit package!"
  let nwords = data.len div 2

  var
    res_ba = createBitarray(48)
  for i in 0 ..< nwords:
    # rest bit array
    res_ba[0..47] = 0
    # can just assign the values of data to the Bitarray, because they are
    # also `uint`.
    let
      d1 = bitwordToByteSeq(data[2 * i], 32)
      d2 = bitwordToByteSeq(data[2 * i + 1], 32)

    res_ba[40 .. 47] = d2[0]
    res_ba[32 .. 39] = d2[1]
    res_ba[24 .. 31] = d2[2]
    res_ba[16 .. 23] = d1[0]
    res_ba[8 .. 15]  = d1[1]
    res_ba[0 .. 7]   = d1[2]
    #echo &"Result {i} is {res_ba.toByteList}"
    buffer[i] = res_ba[0..47]

  # now decode the data
  decode(buffer)

# proc initThread*() {.exportc, dynlib.} =
#   # perform necessary steps for Nim's GC
#   var locals {.volatile.}: pointer
#   setStackBottom(addr(locals))

proc testPtr(a: array[4, uint64]) =
  echo a

proc testArray*(): ptr uint64 {.exportc, dynlib.} =
  var res = cast[array[4, uint64]](alloc0(4 * sizeof(uint64)))
  echo "done"
  res[0] = 0'u64
  res[1] = 1'u64
  res[2] = 2'u64
  res[3] = 128'u64
  result = addr(res[0])

proc testSeq*(): (array[4, uint64], uint8) {.exportc, dynlib.} =
  var res = cast[array[4, uint64]](alloc0(4 * sizeof(uint64)))
  echo "done"
  res[0] = 0'u64
  res[1] = 1'u64
  res[2] = 2'u64
  res[3] = 128'u64
  #result = (addr(res[0]), 4'u8)
  result = (res, 4'u8)

proc grayEncode*(val: uint64): uint64 =
  result = val xor (val shr 1)

proc grayDecode*(val: BitArray): BitArray =
  result = createBitarray(48)
  result[47] = val[47]
  for i in countdown(46, 0):
    result[i] = result[i+1] xor val[i]

proc grayDecode*(val: SomeInteger): uint16 =
  let encodedValue = val.uint16
  result = 0'u16
  result = (encodedValue shr 13'u16) shl 13'u16
  for i in countdown(12, -1):
    result = result or (
      ( ((result shr (i + 1).uint16) and 0x1'u16) xor
        ((encodedValue shr i.uint16) and 0x1'u16)
      ) shl i.uint16
    )

proc destroy*(data: ptr uint64) {.exportc, dynlib.} =
  dealloc(data)

when isMainModule:

  let d = @[16777216'u32, 12401]

  var b = createBitarray(48)
  b[40 .. 47] = 255
  doAssert b[40 .. 47] == 255
  # get the words and convert to seqs
  let
    d1 = bitwordToByteSeq(d[0], 32)
    d2 = bitwordToByteSeq(d[1], 32)
  doAssert d2 == @[113'u, 48, 0, 0]
  doAssert d1 == @[0'u, 0, 0, 1]
  # assign data
  b[40 .. 47] = d2[0]
  doAssert b[40 .. 47] == 113
  b[32 .. 39] = d2[1]
  doAssert b[32 .. 39] == 48
  b[24 .. 31] = d2[2]
  doAssert b[24 .. 31] == 0
  b[16 .. 23] = d1[0]
  doAssert b[16 .. 23] == 0
  b[8 .. 15]  = d1[1]
  doAssert b[8 .. 15] == 0
  b[0 .. 7]   = d1[2]
  doAssert b[0 .. 7] == 0
  var outBuf = newSeq[uint64](2)

  import times
  let t0 = cpuTime()
  for i in 0 .. 10_000:
    decode_fpga(d, outBuf)
  let t1 = cpuTime()
  echo "Decode took ", ((t1 - t0) / 10_000.0), " per call"

  decode_fpga(d, outBuf)

  #doAssert outBuf[0] == 124450972368896'u64
  #doAssert outBuf[1] == 0'u64

  # convert value back to another bitArray and check byte list
  var b2 = createBitarray(48)
  b2[0 .. 47] = outBuf[0]
  #doAssert b2.toByteList == @[0'u, 0, 0, 0, 48, 113]

  let n1 = 10'u64
  let n1_enc = grayEncode(n1)
  echo "N1 grayEncoded is ", n1_enc
  var n1_ba = createBitarray(48)
  n1_ba[0..47] = n1_enc
  echo "N1 grayEncoded bitarray ", n1_ba
  let n1_enc_grayDecode = grayDecode(n1_ba)
  echo "N1 grayDecoded again is ", n1_enc_grayDecode
  echo n1_enc_grayDecode[0..47]

  let tstart = cpuTime()
  for i in 0 .. 1_000_000:
    let
      val = rand(2 ^ 48).uint64
      val_enc = grayEncode(val)
    var val_ba = createBitarray(48)
    val_ba[0..47] = val_enc
    doAssert val_ba.grayDecode[0..47].uint64 == val
  let tstop = cpuTime()

  echo "Time for 1 Mio grayEncodes and grayDecodes is ", (tstop - tstart)
