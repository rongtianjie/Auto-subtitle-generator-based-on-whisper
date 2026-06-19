#!/bin/bash

# 创建用于测试的样本音频文件
# 这使用 ffmpeg 生成一个 2 秒的测试音频

ffmpeg -f lavfi -i sine=frequency=440:duration=2 \
  -f lavfi -i anullsrc=r=44100:cl=mono:duration=2 \
  -c:a libmp3lame -b:a 128k \
  -c:v copy \
  sample.mp3

echo "✓ 测试样本文件 sample.mp3 已生成"
