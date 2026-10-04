import Ajv2020 from 'ajv/dist/2020';
import extractionSchema from '../../contracts/extraction-result.schema.json';
import profileSchema from '../../contracts/structured-profile.schema.json';
import type { ExtractionResult, PreparedResume } from './types';

const validator = new Ajv2020({ strict: false });
validator.addFormat('uuid', /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
const validExtraction = validator.compile<ExtractionResult>(extractionSchema);
const validProfile = validator.compile<PreparedResume>(profileSchema);

function normalizedResume(text: string): string {
  return text.normalize('NFC').replace(/\r\n?/g, '\n').replace(/\u00a0/g, ' ')
    .replace(/\p{Cc}/gu, character => character === '\n' || character === '\t' ? character : '')
    .split('\n').map(line => line.replace(/[ \t]+/g, ' ').trim()).join('\n').replace(/\n{3,}/g, '\n\n').trim();
}

export function parseExtraction(value: unknown): ExtractionResult {
  if (!validExtraction(value)) throw new Error('The server returned invalid extracted resume data. Please retry extraction.');
  return value;
}

export function parseProfile(value: unknown, resumeText: string, jobDescription: string): PreparedResume {
  if (!validProfile(value) || value.resume_text !== normalizedResume(resumeText) || value.job_description !== jobDescription.trim()) {
    throw new Error('The server returned invalid or mismatched resume analysis. Please retry.');
  }
  return value;
}

export function parseDemoJob(value: unknown): string {
  if (!value || typeof value !== 'object' || !('job_description' in value) || typeof value.job_description !== 'string' || value.job_description.trim().length < 100 || value.job_description.length > 20000) {
    throw new Error('The example job description is invalid. Please retry loading the example.');
  }
  return value.job_description;
}
