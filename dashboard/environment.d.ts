// https://stackoverflow.com/a/53981706/16497018

declare global {
  namespace NodeJS {
    interface ProcessEnv {
      NEXT_PUBLIC_ACTIVATION_API: string;
    }
  }
}

// If this file has no import/export statements (i.e. is a script)
// convert it into a module by adding an empty export statement.
export {};
