"use client";

import React from "react";
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
import { AlertTriangle, ShieldAlert } from "lucide-react";

export function DevelopmentNoteDialog() {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          id="dev-note-btn"
          className="border-amber-500/40 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 hover:text-amber-200 text-xs font-bold flex items-center gap-1.5 h-8 px-3 rounded-lg shadow-sm transition-all"
        >
          <AlertTriangle size={13} className="text-amber-400 shrink-0" />
          <span>Development Note</span>
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent className="max-w-md bg-surface border border-border text-foreground rounded-2xl shadow-2xl p-6">
        <div className="flex items-start gap-3.5">
          <div className="p-2.5 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-400 shrink-0 mt-0.5">
            <ShieldAlert size={22} />
          </div>
          <AlertDialogHeader className="space-y-2 text-left">
            <AlertDialogTitle className="text-base font-extrabold text-foreground">
              Development In Progress
            </AlertDialogTitle>
            <AlertDialogDescription className="text-xs leading-relaxed text-foreground/80 space-y-2.5">
              <span className="block text-foreground/70">
                Please be aware that this project is currently under active development. All platform features and administrative tools are temporarily open and accessible to anyone with the direct link.
              </span>
              <span className="block bg-amber-500/10 text-amber-300/90 p-3 rounded-xl border border-amber-500/25 leading-relaxed font-medium">
                <strong>Confidential Notice:</strong> This preview build contains open endpoints and debug configurations that make it vulnerable. Please keep this link to yourself and refrain from sharing it publicly until full production hardening and security measures are completed.
              </span>
              <span className="block text-foreground/60 text-[11px]">
                The current hosting server is provisioned for testing and won't be able to handle heavy external load right now.
              </span>
            </AlertDialogDescription>
          </AlertDialogHeader>
        </div>
        <AlertDialogFooter className="mt-4 pt-3 border-t border-border flex sm:justify-end">
          <AlertDialogAction className="bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs px-4 py-2 rounded-lg transition-colors shadow-md shadow-amber-600/20">
            Acknowledge & Proceed
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
