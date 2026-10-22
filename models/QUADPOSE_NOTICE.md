# QuadPose F2 checkpoint

The analysis server downloads `quadpose_f2.onnx` at build time. The file is
not stored in git.

- Project: https://github.com/EstevanSL/snapml-quadruped-pose
- Commit: `52f0329b5c9af513b5a8f2820aaea6bbd945d0c0`
- File: `models/quadpose_f2.onnx`
- SHA-256: `f3807433962d8abcee18f1bd45e5ff9e56bd899768b03a6996c3db4ebd12b884`
- License: Apache-2.0
- Copyright 2026 Sausage Labs

The publisher states that the pose weights were trained on AP-10K.

AP-10K: A Benchmark for Animal Pose Estimation in the Wild
Hang Yu, Yufei Xu, Jing Zhang, Wei Zhao, Ziyu Guan, Dacheng Tao
NeurIPS 2021 Datasets and Benchmarks Track
https://github.com/AlexTheBad/AP-10K
Annotations: CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/

AP-10K photographs are not in this repository. The publisher's NOTICE also
attributes a ViTPose teacher (Apache-2.0) and MobileNetV2 ImageNet
initialization. Snap's animal detector is not downloaded and is not covered
by the Apache-2.0 grant.

MoveNet Thunder is a separate human-pose model. It is not this checkpoint.
