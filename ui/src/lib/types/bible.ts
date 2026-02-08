// Bible-specific TypeScript interfaces

export type Translation = 'kjv' | 'asv' | 'bbe' | 'ylt' | 'webster';

export interface BibleSearchResult {
	// Core data from Prism
	verse_ref: string;           // "John 3:16"
	book: string;                 // "John"
	chapter: number;              // 3
	verse: number;                // 16
	translation: Translation;     // "kjv"
	text: string;                 // Verse content
	similarity: number;           // 0.0-1.0
	chunk_id?: string;            // Prism chunk ID

	// LLM-generated (cached, optional)
	commentary?: string;
	cross_refs?: CrossReference[];
	translation_insights?: string;

	// UI metadata
	bookmarked?: boolean;
	notes?: string;
	highlight_color?: HighlightColor;
}

export interface CrossReference {
	verse_ref: string;
	relation_type: 'parallel' | 'quote' | 'thematic' | 'contrast';
	explanation: string;
}

export type HighlightColor = 'yellow' | 'green' | 'blue' | 'red' | 'purple';

export interface ThematicSummary {
	themes: string[];
	testament_balance: 'Mostly NT' | 'Balanced' | 'Mostly OT';
	key_books: string[];
	perspective: string;
	surprises?: string;
}

export interface SearchFilters {
	translations: Translation[];
	top_k: number;
}

export interface TranslationComparison {
	verse_ref: string;
	book: string;
	chapter: number;
	verse: number;
	translations: Record<Translation, string>;
	insights?: string;
}

// Prism API response types
export interface PrismSearchResponse {
	results: Array<{
		chunk_id: string;
		document_id: string;
		document_title: string;  // Format: "Book Chapter:Verse (Translation)"
		content: string;
		domain: string;
		tokens: number;
		similarity: number;
	}>;
	total_results: number;
	query: string;
}

// Ollama API types
export interface OllamaGenerateRequest {
	model: string;
	prompt: string;
	stream?: boolean;
	format?: 'json';
	options?: {
		temperature?: number;
		top_p?: number;
		max_tokens?: number;
	};
}

export interface OllamaGenerateResponse {
	model: string;
	created_at: string;
	response: string;
	done: boolean;
}
