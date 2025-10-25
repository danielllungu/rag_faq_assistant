import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject, catchError, throwError } from 'rxjs';

export interface HealthCheckResponse {
  status: string;
  database: string;
  timestamp: string;
}

export interface AskQuestionPayload {
  question: string;
  generate_variants?: boolean;
  num_variants?: number;
}

export interface FaqMatch {
  id: string | number;
  question: string;
  answer: string;
  confidence: number;
}

export interface QuestionResponse {
  answer: string;
  source: 'database' | 'llm';
  confidence: number;
  matched_faq?: FaqMatch | null;
  all_matches?: FaqMatch[];
  generated_variants?: string[];
  processing_time_ms?: number;
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly storageKey = 'faq-rag-api-key';
  private readonly baseUrl = 'http://localhost:8000'; // Adjust when deploying
  private apiKeySubject = new BehaviorSubject<string | null>(this.readStoredApiKey());

  readonly apiKey$ = this.apiKeySubject.asObservable();

  get apiKey(): string | null {
    return this.apiKeySubject.value;
  }

  setApiKey(key: string): void {
    const trimmed = key.trim();
    this.apiKeySubject.next(trimmed);
    if (this.canUseStorage()) {
      localStorage.setItem(this.storageKey, trimmed);
    }
  }

  clearApiKey(): void {
    this.apiKeySubject.next(null);
    if (this.canUseStorage()) {
      localStorage.removeItem(this.storageKey);
    }
  }

  healthCheck(): Observable<HealthCheckResponse> {
    return this.http.get<HealthCheckResponse>(`${this.baseUrl}/health`).pipe(
      catchError((error) => this.handleError(error))
    );
  }

  askQuestion(payload: AskQuestionPayload): Observable<QuestionResponse> {
    return this.http.post<QuestionResponse>(
      `${this.baseUrl}/faq/ask`,
      payload,
      { headers: this.buildHeaders() }
    ).pipe(
      catchError((error) => this.handleError(error))
    );
  }

  searchFaqs(query: string, generateVariants = true, numVariants = 3): Observable<QuestionResponse> {
    const params = new URLSearchParams({
      q: query,
      generate_variants: String(generateVariants),
      num_variants: String(numVariants)
    });

    return this.http.get<QuestionResponse>(
      `${this.baseUrl}/faq/search?${params.toString()}`,
      { headers: this.buildHeaders() }
    ).pipe(
      catchError((error) => this.handleError(error))
    );
  }

  private buildHeaders(): HttpHeaders {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };

    if (this.apiKey) {
      headers['X-API-Key'] = this.apiKey;
    }

    return new HttpHeaders(headers);
  }

  private handleError(error: HttpErrorResponse) {
    if (error.status === 401) {
      this.clearApiKey();
    }

    return throwError(() => error);
  }

  private readStoredApiKey(): string | null {
    try {
      if (!this.canUseStorage()) {
        return null;
      }

      const stored = localStorage.getItem(this.storageKey);
      return stored && stored.trim().length ? stored : null;
    } catch {
      return null;
    }
  }

  private canUseStorage(): boolean {
    return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
  }
}
