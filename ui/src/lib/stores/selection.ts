// Selected verse state management

import { writable, derived } from 'svelte/store';
import type { BibleSearchResult, Translation } from '$lib/types/bible';

// Currently selected verse
export const selectedVerse = writable<BibleSearchResult | null>(null);

// Translations to compare
export const compareTranslations = writable<Translation[]>(['kjv', 'asv', 'bbe', 'ylt']);

// Translation comparison data
export const comparisonData = writable<Record<Translation, string>>({});

// Loading states for AI features
export const loadingCommentary = writable<boolean>(false);
export const loadingCrossRefs = writable<boolean>(false);
export const loadingTranslationInsights = writable<boolean>(false);

// Derived: has selection
export const hasSelection = derived(
	selectedVerse,
	($verse) => $verse !== null
);

/**
 * Select a verse for detailed view
 */
export function selectVerse(verse: BibleSearchResult) {
	selectedVerse.set(verse);
	comparisonData.set({});  // Reset comparison data
}

/**
 * Clear selection
 */
export function clearSelection() {
	selectedVerse.set(null);
	comparisonData.set({});
}

/**
 * Toggle translation in comparison
 */
export function toggleCompareTranslation(translation: Translation) {
	compareTranslations.update(translations => {
		const updated = [...translations];
		const index = updated.indexOf(translation);

		if (index > -1) {
			// Remove if present (but keep at least one)
			if (updated.length > 1) {
				updated.splice(index, 1);
			}
		} else {
			// Add if not present (max 4 translations)
			if (updated.length < 4) {
				updated.push(translation);
			}
		}

		return updated;
	});
}
