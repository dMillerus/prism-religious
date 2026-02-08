// Ollama API client for LLM-generated Bible insights

import type {
	OllamaGenerateRequest,
	OllamaGenerateResponse,
	CrossReference,
	ThematicSummary,
	BibleSearchResult,
	Translation
} from '$lib/types/bible';

const OLLAMA_API_URL = import.meta.env.VITE_OLLAMA_API_URL || 'http://ollama:11434';
const DEFAULT_MODEL = 'qwen2.5:14b';

/**
 * Generate contextual commentary for a Bible verse
 */
export async function generateCommentary(
	verse: string,
	reference: string,
	translation: string
): Promise<string> {
	const prompt = `Given this Bible verse:
"${verse}"
From: ${reference} (${translation})

Provide concise commentary (2-3 paragraphs) covering:
1. Historical context (when, where, who)
2. Literary context (what comes before/after)
3. Theological significance
4. Practical application

Be factual and balanced. Cite related passages when relevant. Keep it under 300 words.`;

	try {
		const response = await fetch(`${OLLAMA_API_URL}/api/generate`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				model: DEFAULT_MODEL,
				prompt,
				stream: false,
				options: {
					temperature: 0.3,  // Lower = more factual
					top_p: 0.9
				}
			} as OllamaGenerateRequest)
		});

		if (!response.ok) {
			throw new Error(`Ollama API error: ${response.statusText}`);
		}

		const data: OllamaGenerateResponse = await response.json();
		return data.response;
	} catch (error) {
		console.error('Commentary generation failed:', error);
		return 'Commentary generation unavailable. Please try again later.';
	}
}

/**
 * Find cross-references for a Bible verse
 */
export async function findCrossReferences(
	verse: string,
	reference: string
): Promise<CrossReference[]> {
	const prompt = `Given this Bible verse:
"${verse}" (${reference})

Find 5-7 related Bible passages that:
- Quote or reference this verse
- Share similar themes or vocabulary
- Provide parallel accounts (for Gospels)
- Offer theological connections

Return ONLY valid JSON array with no extra text:
[
  {
    "verse_ref": "Book Chapter:Verse",
    "relation_type": "quote",
    "explanation": "brief 1-sentence explanation"
  }
]

relation_type must be one of: "quote", "thematic", "parallel", "contrast"`;

	try {
		const response = await fetch(`${OLLAMA_API_URL}/api/generate`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				model: DEFAULT_MODEL,
				prompt,
				format: 'json',
				stream: false,
				options: {
					temperature: 0.2
				}
			} as OllamaGenerateRequest)
		});

		if (!response.ok) {
			throw new Error(`Ollama API error: ${response.statusText}`);
		}

		const data: OllamaGenerateResponse = await response.json();

		// Parse JSON response
		try {
			const parsed = JSON.parse(data.response);
			if (Array.isArray(parsed)) {
				return parsed as CrossReference[];
			}
			return [];
		} catch (parseError) {
			console.error('Failed to parse cross-references JSON:', data.response);
			return [];
		}
	} catch (error) {
		console.error('Cross-reference generation failed:', error);
		return [];
	}
}

/**
 * Compare translations and generate insights
 */
export async function compareTranslations(
	reference: string,
	translations: Record<Translation, string>
): Promise<string> {
	const translationText = Object.entries(translations)
		.map(([name, text]) => `${name.toUpperCase()}: "${text}"`)
		.join('\n\n');

	const prompt = `Compare these translations of ${reference}:

${translationText}

Explain (2-3 paragraphs, under 250 words):
1. Key word differences and their significance
2. Which is more literal vs. dynamic equivalence
3. Any theological implications of the differences
4. Etymology of key terms (Hebrew/Greek roots)

Be specific about which translation choices are more accurate.`;

	try {
		const response = await fetch(`${OLLAMA_API_URL}/api/generate`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				model: DEFAULT_MODEL,
				prompt,
				stream: false,
				options: {
					temperature: 0.3,
					top_p: 0.9
				}
			} as OllamaGenerateRequest)
		});

		if (!response.ok) {
			throw new Error(`Ollama API error: ${response.statusText}`);
		}

		const data: OllamaGenerateResponse = await response.json();
		return data.response;
	} catch (error) {
		console.error('Translation comparison failed:', error);
		return 'Translation comparison unavailable. Please try again later.';
	}
}

/**
 * Summarize search results thematically
 */
export async function summarizeSearchResults(
	query: string,
	results: BibleSearchResult[]
): Promise<ThematicSummary> {
	const topVerses = results.slice(0, 10)
		.map(r => `- ${r.verse_ref}: "${r.text.slice(0, 100)}${r.text.length > 100 ? '...' : ''}"`)
		.join('\n');

	const prompt = `User searched for: "${query}"
Found ${results.length} Bible passages.

Top 10 results:
${topVerses}

Analyze these passages and provide ONLY valid JSON with no extra text:
{
  "themes": ["theme 1", "theme 2", "theme 3"],
  "testament_balance": "Mostly NT" or "Balanced" or "Mostly OT",
  "key_books": ["Book 1", "Book 2", "Book 3"],
  "perspective": "2-sentence summary",
  "surprises": "1-sentence insight or omit if none"
}`;

	try {
		const response = await fetch(`${OLLAMA_API_URL}/api/generate`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				model: DEFAULT_MODEL,
				prompt,
				format: 'json',
				stream: false,
				options: {
					temperature: 0.3
				}
			} as OllamaGenerateRequest)
		});

		if (!response.ok) {
			throw new Error(`Ollama API error: ${response.statusText}`);
		}

		const data: OllamaGenerateResponse = await response.json();

		try {
			const parsed = JSON.parse(data.response);
			return parsed as ThematicSummary;
		} catch (parseError) {
			console.error('Failed to parse summary JSON:', data.response);
			return {
				themes: ['Unable to generate summary'],
				testament_balance: 'Balanced',
				key_books: [],
				perspective: 'Summary generation failed. Please try again.'
			};
		}
	} catch (error) {
		console.error('Summary generation failed:', error);
		return {
			themes: ['Error generating summary'],
			testament_balance: 'Balanced',
			key_books: [],
			perspective: 'Summary generation unavailable. Please try again later.'
		};
	}
}

/**
 * Check if Ollama is available
 */
export async function checkHealth(): Promise<boolean> {
	try {
		const response = await fetch(`${OLLAMA_API_URL}/api/tags`);
		return response.ok;
	} catch (error) {
		console.error('Ollama health check failed:', error);
		return false;
	}
}
