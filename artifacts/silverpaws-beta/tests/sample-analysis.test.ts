import assert from 'node:assert/strict';
import test from 'node:test';

import { createSampleAnalysis, SAMPLE_DATA_LABEL } from '../src/lib/sample-analysis.ts';

test('demo result has labeled mock factors and pose keypoints', () => {
  const sample = createSampleAnalysis();

  assert.equal(sample.demo, true);
  assert.equal(SAMPLE_DATA_LABEL, 'Sample data — not your pet');
  assert.equal(sample.pipeline, 'quadpose');
  assert.equal(sample.factors && Object.keys(sample.factors).length, 5);
  assert.ok(Object.values(sample.factors ?? {}).every((score) => typeof score === 'number' && score >= 0 && score <= 100));
  assert.ok((sample.measurements?.poseKeypoints?.length ?? 0) > 0);
  assert.match(sample.observation ?? '', /sample/i);
});
