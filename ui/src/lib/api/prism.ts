// Prism API client for Bible search

import type { PrismSearchResponse, BibleSearchResult, Translation } from '$lib/types/bible';

const PRISM_API_URL = import.meta.env.VITE_PRISM_API_URL || 'http://prism:8100';

/**
 * Parse verse reference from document title
 * Format: "Book Chapter:Verse (Translation)"
 * Example: "I Corinthians 13:13 (KJV)"
 */
function parseVerseRef(documentTitle: string): { book: string; chapter: number; verse: number; ref: string } | null {
	// Extract parts before the parentheses
	const match = documentTitle.match(/^(.+?)\s+(\d+):(\d+)(?:-(\d+))?\s*\(/);

	if (!match) {
		return null;
	}

	const book = match[1].trim();
	const chapter = parseInt(match[2]);
	const verse = parseInt(match[3]);

	return {
		book,
		chapter,
		verse,
		ref: `${book} ${chapter}:${verse}`
	};
}

/**
 * Search Bible across selected translations
 * Since Prism doesn't support multiple domains in one call, we make parallel requests
 */
export async function searchBible(
	query: string,
	translations: Translation[] = ['kjv', 'asv', 'bbe', 'ylt', 'webster'],
	topK: number = 20
): Promise<BibleSearchResult[]> {
	// Make parallel requests for each translation
	const requests = translations.map(async (translation) => {
		const response = await fetch(`${PRISM_API_URL}/api/v1/search`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				query,
				domain: `bible/${translation.toLowerCase()}`,
				top_k: topK
			})
		});

		if (!response.ok) {
			console.error(`Search failed for ${translation}: ${response.statusText}`);
			return [];
		}

		const data: PrismSearchResponse = await response.json();

		return data.results.map((result) => {
			const verseInfo = parseVerseRef(result.document_title);

			if (!verseInfo) {
				console.warn('Invalid verse reference in title:', result.document_title);
				return null;
			}

			return {
				verse_ref: verseInfo.ref,
				book: verseInfo.book,
				chapter: verseInfo.chapter,
				verse: verseInfo.verse,
				translation: translation,
				text: result.content,
				similarity: result.similarity,
				chunk_id: result.chunk_id
			} as BibleSearchResult;
		}).filter((r): r is BibleSearchResult => r !== null);
	});

	const results = await Promise.all(requests);

	// Flatten and sort by similarity
	const allResults = results.flat().sort((a, b) => b.similarity - a.similarity);

	// Return top K overall results
	return allResults.slice(0, topK);
}

/**
 * Get specific verse in multiple translations for comparison
 */
export async function getVerseInTranslations(
	book: string,
	chapter: number,
	verse: number,
	translations: Translation[] = ['kjv', 'asv', 'bbe', 'ylt']
): Promise<Record<Translation, string>> {
	const query = `${book} ${chapter}:${verse}`;

	const requests = translations.map(async (translation) => {
		const response = await fetch(`${PRISM_API_URL}/api/v1/search`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				query,
				domain: `bible/${translation.toLowerCase()}`,
				top_k: 1
			})
		});

		if (!response.ok) {
			console.error(`Fetch failed for ${translation}: ${response.statusText}`);
			return { translation, text: 'Error loading verse' };
		}

		const data: PrismSearchResponse = await response.json();

		if (data.results.length === 0) {
			return { translation, text: 'Verse not found' };
		}

		return { translation, text: data.results[0].content };
	});

	const results = await Promise.all(requests);

	// Convert to record
	const translationMap: Record<string, string> = {};
	results.forEach(({ translation, text }) => {
		translationMap[translation] = text;
	});

	return translationMap as Record<Translation, string>;
}

/**
 * Check Prism health status
 */
export async function checkHealth(): Promise<boolean> {
	try {
		const response = await fetch(`${PRISM_API_URL}/health`);
		return response.ok;
	} catch (error) {
		console.error('Health check failed:', error);
		return false;
	}
}
