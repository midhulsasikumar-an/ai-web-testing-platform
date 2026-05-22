import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface CommentBoxProps {
  onSubmit: (body: string) => Promise<void>;
  placeholder?: string;
}

export function CommentBox({ onSubmit, placeholder = "Add a comment..." }: CommentBoxProps) {
  const [text, setText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!text.trim()) return;
    setIsSubmitting(true);
    try {
      await onSubmit(text);
      setText('');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-2 mt-4">
      <Textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={placeholder}
        className="min-h-[80px]"
      />
      <div className="flex justify-end">
        <Button onClick={handleSubmit} disabled={!text.trim() || isSubmitting}>
          {isSubmitting ? "Posting..." : "Comment"}
        </Button>
      </div>
    </div>
  );
}
