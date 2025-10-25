import { ChangeDetectionStrategy, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-api-key',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './api-key.component.html',
  styleUrl: './api-key.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ApiKeyComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  protected readonly apiService = inject(ApiService);

  readonly form = this.fb.nonNullable.group({
    apiKey: ['', [Validators.required, Validators.minLength(4)]]
  });

  isSubmitting = false;
  errorMessage: string | null = null;

  ngOnInit(): void {
    const existingKey = this.apiService.apiKey;
    if (existingKey) {
      this.form.patchValue({ apiKey: existingKey });
    }

  }

  healthCheck() {
    this.apiService.healthCheck().subscribe({
      next: () => {
        console.log('Health check successful.');
      },
      error: (err) => {
        this.errorMessage = 'API key is invalid or there was an error connecting to the API.';
        console.error(err);
      }
    });
  }

  submit(): void {
    this.errorMessage = null;
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const apiKey = this.form.controls.apiKey.value.trim();
    if (!apiKey) {
      this.form.controls.apiKey.setErrors({ required: true });
      return;
    }

    this.isSubmitting = true;

    try {
      this.apiService.setApiKey(apiKey);
      this.router.navigate(['/chat']);
    } catch (error) {
      this.errorMessage = 'Failed to store API key. Please try again.';
      console.error(error);
    } finally {
      this.isSubmitting = false;
    }
  }

  clearSavedKey(): void {
    this.apiService.clearApiKey();
    this.form.reset();
  }
}
