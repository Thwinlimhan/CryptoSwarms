import { test, expect } from 'vitest';
import { API_URL } from '../config';

test('API_URL is defined', () => {
  expect(API_URL).toBeDefined();
  expect(typeof API_URL).toBe('string');
});
