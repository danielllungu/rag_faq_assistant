import { AfterViewInit, ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, ElementRef, OnInit, PLATFORM_ID, ViewChild, inject } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ApiService, QuestionResponse } from '../../services/api.service';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';

type MessageRole = 'user' | 'assistant' | 'system';

interface ChatMessage {
  role: MessageRole;
  content: string;
  timestamp: Date;
  response?: QuestionResponse;
  matchScore?: number | null;
}

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ChatComponent implements OnInit, AfterViewInit {
  @ViewChild('messagesContainer') private messagesContainer?: ElementRef<HTMLDivElement>;
  @ViewChild('composerInput') private composerInput?: ElementRef<HTMLTextAreaElement>;

  private readonly fb = inject(FormBuilder);
  private readonly apiService = inject(ApiService);
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly isBrowser = isPlatformBrowser(inject(PLATFORM_ID));
  private readonly destroyRef = inject(DestroyRef);

  readonly form = this.fb.nonNullable.group({
    question: ['', [Validators.required, Validators.maxLength(1000)]]
  });

  messages: ChatMessage[] = [];
  isLoading = false;
  errorMessage: string | null = null;

  ngOnInit(): void {
    if (!this.apiService.apiKey) {
      this.router.navigate(['/']);
      return;
    }

    this.pushSystemMessage('Ask a question and I will search our FAQs for you.');
  }

  ngAfterViewInit(): void {
    this.autoResize();
  }

  get maskedApiKey(): string {
    const key = this.apiService.apiKey;
    if (!key) {
      return '';
    }

    if (key.length <= 6) {
      return '*'.repeat(Math.max(0, key.length - 2)) + key.slice(-2);
    }

    return `${key.slice(0, 3)}••••${key.slice(-2)}`;
  }

  submit(): void {
    this.errorMessage = null;
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const question = this.form.controls.question.value.trim();
    if (!question) {
      this.form.controls.question.setErrors({ required: true });
      return;
    }

    this.appendMessage({
      role: 'user',
      content: question,
      timestamp: new Date()
    });

    this.form.reset({ question: '' });
    this.autoResize();
    this.isLoading = true;
    this.apiService.askQuestion({ question })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => this.handleResponse(response),
        error: (error) => this.handleError(error, question)
      });
  }

  handleKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.submit();
    }
  }

  autoResize(): void {
    if (!this.isBrowser) {
      return;
    }

    queueMicrotask(() => {
      const textarea = this.composerInput?.nativeElement;
      if (!textarea) {
        return;
      }
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 320)}px`;
    });
  }

  retry(): void {
    this.apiService.clearApiKey();
    this.router.navigate(['/']);
  }

  trackByIndex(_index: number, item: ChatMessage): string {
    return `${item.role}-${item.timestamp.getTime()}`;
  }

  private handleResponse(response: QuestionResponse): void {
    this.isLoading = false;
    this.errorMessage = null;

    this.appendMessage({
      role: 'assistant',
      content: response.answer,
      timestamp: new Date(),
      response,
      matchScore: response.source === 'llm' ? null : this.getTopMatchScore(response)
    });

    this.cdr.markForCheck();
  }

  private getTopMatchScore(response: QuestionResponse): number | null {
    const scores: number[] = [];

    const primaryScore = this.extractMatchScore(response.matched_faq);
    if (primaryScore !== null) {
      scores.push(primaryScore);
    }

    if (Array.isArray(response.all_matches)) {
      for (const match of response.all_matches) {
        const score = this.extractMatchScore(match);
        if (score !== null) {
          scores.push(score);
        }
      }
    }

    if (!scores.length) {
      return null;
    }

    return Math.max(...scores);
  }

  private extractMatchScore(match: unknown): number | null {
    if (!match || typeof match !== 'object') {
      return null;
    }

    const record = match as Record<string, unknown>;
    const byConfidence = record['confidence'];
    if (typeof byConfidence === 'number') {
      return byConfidence;
    }

    const bySimilarity = record['similarity'];
    if (typeof bySimilarity === 'number') {
      return bySimilarity;
    }

    return null;
  }

  private handleError(error: unknown, question: string): void {
    this.isLoading = false;

    if (error instanceof HttpErrorResponse && error.status === 401) {
      this.errorMessage = 'Authentication failed. Please enter your API key again.';
      this.pushSystemMessage('Your session expired. Please provide your API key once more.');
      this.router.navigate(['/']);
      return;
    }

    const message = error instanceof HttpErrorResponse
      ? error.error?.detail || error.message || 'Unexpected error while contacting the assistant.'
      : 'Unexpected error while contacting the assistant.';

    this.errorMessage = message;

    this.appendMessage({
      role: 'system',
      content: `There was a problem answering "${question}". ${message}`,
      timestamp: new Date()
    });

    this.cdr.markForCheck();
  }

  private pushSystemMessage(content: string): void {
    this.appendMessage({
      role: 'system',
      content,
      timestamp: new Date()
    });
  }

  private appendMessage(message: ChatMessage): void {
    this.messages = [...this.messages, message];
    this.cdr.markForCheck();
    this.scrollToBottom();
  }

  private scrollToBottom(): void {
    if (!this.isBrowser) {
      return;
    }

    queueMicrotask(() => {
      const container = this.messagesContainer?.nativeElement;
      if (container) {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: 'smooth'
        });
      }
    });
  }
}
