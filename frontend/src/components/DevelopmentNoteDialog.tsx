"use client";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";

export function DevelopmentNoteDialog() {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="outline" size="sm" id="dev-note-btn" className="text-xs">
          Development note
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader className="space-y-2 text-left">
          <AlertDialogTitle className="font-serif text-lg font-semibold">
            Development in progress
          </AlertDialogTitle>
          <AlertDialogDescription className="space-y-2.5 text-sm leading-relaxed text-foreground/70">
            <span className="block">
              This project is under active development. Platform features and administrative tools
              are open to anyone with the direct link.
            </span>
            <span className="block border-l-2 border-accent bg-background px-3 py-2 text-foreground">
              Confidential notice: this preview build contains open endpoints and debug
              configuration. Keep the link private until production hardening is finished.
            </span>
            <span className="block text-xs text-foreground/55">
              The current host is provisioned for testing and will not handle a heavy external load.
            </span>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="mt-4 border-t border-border pt-3 sm:justify-end">
          <AlertDialogAction>Acknowledge</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
